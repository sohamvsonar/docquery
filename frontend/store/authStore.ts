/**
 * Zustand store for authentication state management
 * Handles login, logout, and user session persistence
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authAPI, clearTokens } from "@/lib/api";
import type { UserResponse, LoginRequest } from "@/types/api";

interface AuthState {
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  fetchCurrentUser: () => Promise<void>;
  clearError: () => void;
}

/**
 * Helper function to extract error message from various error formats
 */
const extractErrorMessage = (error: any): string => {
  // If it's a string, return it
  if (typeof error === "string") {
    return error;
  }

  // FastAPI validation errors (422)
  if (error.response?.status === 422 && error.response?.data?.detail) {
    const detail = error.response.data.detail;

    // If detail is an array of validation errors
    if (Array.isArray(detail)) {
      const firstError = detail[0];
      if (firstError?.msg) {
        return firstError.msg;
      }
      return "Validation error";
    }

    // If detail is a string
    if (typeof detail === "string") {
      return detail;
    }

    // If detail is an object
    if (typeof detail === "object" && detail.msg) {
      return detail.msg;
    }
  }

  // Standard API error with detail string
  if (error.response?.data?.detail && typeof error.response.data.detail === "string") {
    return error.response.data.detail;
  }

  // Axios error with message
  if (error.message) {
    return error.message;
  }

  // Fallback
  return "An error occurred";
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (credentials: LoginRequest) => {
        set({ isLoading: true, error: null });

        try {
          // Login and get tokens (api.ts handles token storage)
          await authAPI.login(credentials);

          // Fetch user details
          const user = await authAPI.getCurrentUser();

          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = extractErrorMessage(error);

          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: errorMessage,
          });

          // Don't throw - just set error in state
          // The UI will display it from the store
        }
      },

      logout: async () => {
        set({ isLoading: true });

        try {
          // Call logout API to blacklist token
          await authAPI.logout();
        } catch (error) {
          console.error("Logout API call failed:", error);
          // Continue with local logout even if API fails
        } finally {
          // Clear local state and tokens
          clearTokens();
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          });
        }
      },

      fetchCurrentUser: async () => {
        set({ isLoading: true, error: null });

        try {
          const user = await authAPI.getCurrentUser();

          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = extractErrorMessage(error);

          // If unauthorized, clear everything
          if (error.response?.status === 401) {
            clearTokens();
            set({
              user: null,
              isAuthenticated: false,
              isLoading: false,
              error: null,
            });
          } else {
            set({
              isLoading: false,
              error: errorMessage,
            });
          }

          // Don't throw - just set error in state
        }
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: "auth-storage", // Name for localStorage key
      partialize: (state) => ({
        // Only persist user and isAuthenticated
        // Don't persist loading or error states
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
