"use client";

/**
 * Main Application Layout
 * Includes sidebar navigation, header, and content area
 */

import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useState } from "react";
import ThemeToggle from "@/components/ThemeToggle";

interface ChatSession {
  id: string;
  title: string;
  messages: any[];
  createdAt: Date;
  updatedAt: Date;
}

interface AppLayoutProps {
  children: React.ReactNode;
  chatSessions?: ChatSession[];
  currentSessionId?: string | null;
  onNewChat?: () => void;
  onSelectSession?: (id: string) => void;
  onDeleteSession?: (id: string) => void;
}

export default function AppLayout({
  children,
  chatSessions = [],
  currentSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
}: AppLayoutProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const [showUserPanel, setShowUserPanel] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  const handleDeleteAccount = async () => {
    if (!user?.id) return;

    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`http://localhost:8000/users/${user.id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        await logout();
        router.push("/login");
      } else {
        const error = await response.json();
        alert(`Failed to delete account: ${error.detail}`);
      }
    } catch (error) {
      console.error("Error deleting account:", error);
      alert("Failed to delete account");
    }
  };

  // Filter nav items based on user role
  const allNavItems = [
    {
      name: "Dashboard",
      path: "/dashboard",
      icon: "📊",
      adminOnly: true,
    },
    {
      name: "Documents",
      path: "/documents",
      icon: "📄",
      adminOnly: false,
    },
    {
      name: "Chat",
      path: "/chat",
      icon: "💬",
      adminOnly: false,
    },
  ];

  const navItems = allNavItems.filter(
    (item) => !item.adminOnly || user?.is_admin
  );

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900 overflow-hidden">
      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={cn(
        "bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col transition-all duration-300",
        // Display behavior
        isMobileMenuOpen ? "flex w-64" : "hidden",
        "lg:flex",
        // Widths
        isCollapsed ? "lg:w-16" : "lg:w-64",
        // Positioning
        "fixed inset-y-0 left-0 z-50 lg:relative"
      )}>
        {/* Logo/Brand */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          {!isCollapsed && (
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                DocQuery
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {user?.username}
              </p>
            </div>
          )}
          {/* Collapse Button */}
          <button
            onClick={() => {
              if (typeof window !== "undefined" && window.innerWidth < 1024) {
                // On mobile, close the sidebar instead of collapsing width
                setIsMobileMenuOpen(false);
                return;
              }
              setIsCollapsed(!isCollapsed);
            }}
            className={cn(
              "flex items-center justify-center w-8 h-8 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 transition-colors",
              isCollapsed && "mx-auto"
            )}
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <svg
              className={cn("w-5 h-5 transition-transform duration-300", isCollapsed && "rotate-180")}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          {navItems.map((item) => (
            <div key={item.path}>
              <div className={cn("flex items-center", !isCollapsed && "gap-1")}>
                <button
                  onClick={() => {
                    router.push(item.path);
                    if (typeof window !== "undefined" && window.innerWidth < 1024) {
                      setIsMobileMenuOpen(false);
                    }
                  }}
                  className={cn(
                    "flex items-center rounded-lg transition-colors",
                    isCollapsed ? "w-full justify-center px-2 py-3" : "flex-1 gap-3 px-4 py-3 text-left",
                    pathname === item.path
                      ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-medium"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  )}
                  title={isCollapsed ? item.name : undefined}
                >
                  <span className="text-xl">{item.icon}</span>
                  {!isCollapsed && <span>{item.name}</span>}
                </button>

                {/* New Chat Button - Shows only for Chat nav item when not collapsed */}
                {item.path === "/chat" && !isCollapsed && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (pathname !== "/chat") {
                        router.push("/chat?new=true");
                      } else {
                        onNewChat?.();
                      }
                      if (typeof window !== "undefined" && window.innerWidth < 1024) {
                        setIsMobileMenuOpen(false);
                      }
                    }}
                    className="flex items-center justify-center w-8 h-8 rounded-md bg-gradient-to-br from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white shadow-sm hover:shadow-md transition-all duration-200 transform hover:scale-105"
                    title="New Chat"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                    </svg>
                  </button>
                )}
              </div>

              {/* Chat Sessions - Only show when not collapsed */}
              {item.path === "/chat" && chatSessions.length > 0 && !isCollapsed && (
                <div className="mt-2 ml-4 space-y-1">
                  {/* Sessions List */}
                  <div className="space-y-1 max-h-96 overflow-y-auto">
                    {chatSessions.map((session) => (
                      <div
                        key={session.id}
                        onClick={() => {
                          if (pathname !== "/chat") {
                            router.push("/chat");
                          }
                          setTimeout(() => onSelectSession?.(session.id), 100);
                          if (typeof window !== "undefined" && window.innerWidth < 1024) {
                            setIsMobileMenuOpen(false);
                          }
                        }}
                        className={cn(
                          "group flex items-start justify-between px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors",
                          currentSessionId === session.id && pathname === "/chat"
                            ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                            : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                        )}
                      >
                        <div className="flex-1 min-w-0">
                          <p className="truncate font-medium">
                            {session.title}
                          </p>
                          <p className="text-xs opacity-70">
                            {session.messages.length} msgs
                          </p>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteSession?.(session.id);
                          }}
                          className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-700 ml-2 text-lg leading-none"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </nav>

        {/* User Section */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          {!isCollapsed ? (
            <>
              <div className="mb-3 text-sm">
                <p className="text-gray-500 dark:text-gray-400">Signed in as</p>
                <p className="font-medium text-gray-900 dark:text-white truncate">
                  {user?.email || user?.username}
                </p>
                {user?.is_admin && (
                  <span className="inline-block mt-1 px-2 py-0.5 bg-purple-100 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 text-xs rounded">
                    Admin
                  </span>
                )}
              </div>
              <Button onClick={handleLogout} variant="outline" className="w-full">
                Logout
              </Button>
            </>
          ) : (
            <button
              onClick={handleLogout}
              className="flex items-center justify-center w-full px-4 py-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors"
              title="Logout"
            >
              <span className="text-xl">🚪</span>
            </button>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 md:px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400"
              aria-label="Toggle menu"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            <h2 className="text-lg md:text-xl font-semibold text-gray-900 dark:text-white">
              {navItems.find((item) => item.path === pathname)?.name || "DocQuery"}
            </h2>

            {/* Right Side Actions */}
            <div className="flex items-center gap-2 md:gap-4">
              {/* Theme Toggle */}
              <ThemeToggle />

              {/* User Profile Icon */}
              <div className="relative">
              <button
                onClick={() => setShowUserPanel(!showUserPanel)}
                className="flex items-center justify-center w-10 h-10 rounded-full bg-blue-500 text-white font-semibold hover:bg-blue-600 transition-colors"
                title="User Profile"
              >
                {user?.username?.charAt(0).toUpperCase() || "U"}
              </button>

              {/* User Profile Dropdown Panel */}
              {showUserPanel && (
                <>
                  {/* Backdrop to close panel when clicking outside */}
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setShowUserPanel(false)}
                  />

                  {/* Dropdown Panel */}
                  <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-20 overflow-hidden">
                    {/* User Info Section */}
                    <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-b border-gray-200 dark:border-gray-700">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-blue-500 text-white font-bold text-lg">
                          {user?.username?.charAt(0).toUpperCase() || "U"}
                        </div>
                        <div className="flex-1">
                          <p className="font-semibold text-gray-900 dark:text-white">
                            {user?.username}
                          </p>
                          {user?.is_admin && (
                            <span className="inline-block px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 text-xs rounded">
                              Admin
                            </span>
                          )}
                        </div>
                      </div>

                      {/* User Details */}
                      <div className="space-y-2 text-sm">
                        <div>
                          <label className="text-gray-500 dark:text-gray-400 text-xs">
                            Email
                          </label>
                          <p className="text-gray-900 dark:text-white font-medium truncate">
                            {user?.email || "No email provided"}
                          </p>
                        </div>
                        <div>
                          <label className="text-gray-500 dark:text-gray-400 text-xs">
                            Password
                          </label>
                          <p className="text-gray-900 dark:text-white font-medium">
                            ••••••••
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Actions Section */}
                    <div className="p-3 space-y-2">
                      <Button
                        onClick={() => {
                          setShowUserPanel(false);
                          handleLogout();
                        }}
                        variant="outline"
                        className="w-full justify-start"
                      >
                        <span className="mr-2">🚪</span>
                        Logout
                      </Button>

                      {/* Only show delete account for non-admin users */}
                      {!user?.is_admin && (
                        <>
                          {!showDeleteConfirm ? (
                            <Button
                              onClick={() => setShowDeleteConfirm(true)}
                              variant="outline"
                              className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 border-red-200 dark:border-red-800"
                            >
                              <span className="mr-2">🗑️</span>
                              Delete Account & Data
                            </Button>
                          ) : (
                            <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                              <p className="text-sm text-red-800 dark:text-red-200 mb-3 font-medium">
                                Are you sure? This will permanently delete your account and all your data.
                              </p>
                              <div className="flex gap-2">
                                <Button
                                  onClick={() => {
                                    setShowUserPanel(false);
                                    setShowDeleteConfirm(false);
                                    handleDeleteAccount();
                                  }}
                                  size="sm"
                                  className="flex-1 bg-red-600 hover:bg-red-700 text-white"
                                >
                                  Yes, Delete
                                </Button>
                                <Button
                                  onClick={() => setShowDeleteConfirm(false)}
                                  size="sm"
                                  variant="outline"
                                  className="flex-1"
                                >
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </>
              )}
              </div>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-auto p-4 md:p-6">{children}</div>
      </main>
    </div>
  );
}
