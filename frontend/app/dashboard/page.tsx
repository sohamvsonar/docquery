"use client";

/**
 * Dashboard Page
 * Main landing page after successful login
 * Shows user management for admins
 */

import { useEffect, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/components/AppLayout";
import { useAuthStore } from "@/store/authStore";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { usersAPI } from "@/lib/api";
import { UserResponse } from "@/types/api";

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state for creating new user
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newUser, setNewUser] = useState({
    username: "",
    email: "",
    password: "",
    is_admin: false,
  });

  const loadUsers = async () => {
    if (!user?.is_admin) return;

    try {
      setLoading(true);
      setError(null);
      const usersList = await usersAPI.list();
      setUsers(usersList);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, [user?.is_admin]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      await usersAPI.create(newUser);
      setSuccess("User created successfully");
      setNewUser({ username: "", email: "", password: "", is_admin: false });
      setShowCreateForm(false);
      loadUsers();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      console.error("Create user error:", err);

      // Handle validation errors (422)
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;

        // If detail is an array (validation errors)
        if (Array.isArray(detail)) {
          const errorMessages = detail.map((e: any) =>
            `${e.loc?.join(' > ') || 'Field'}: ${e.msg}`
          ).join('; ');
          setError(errorMessages);
        } else if (typeof detail === 'string') {
          setError(detail);
        } else {
          setError("Validation error occurred");
        }
      } else {
        setError(err.message || "Failed to create user");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!confirm("Are you sure you want to delete this user?")) return;

    try {
      setLoading(true);
      setError(null);
      await usersAPI.delete(userId);
      setSuccess("User deleted successfully");
      loadUsers();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete user");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="space-y-6">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert className="bg-green-50 text-green-800 border-green-200">
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
            {/* User Info Card */}
            <Card>
              <CardHeader>
                <CardTitle>User Information</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-2">
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Username</dt>
                    <dd className="text-lg font-semibold text-gray-900 dark:text-white">{user?.username}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Email</dt>
                    <dd className="text-lg font-semibold text-gray-900 dark:text-white">{user?.email || "N/A"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Role</dt>
                    <dd className="text-lg font-semibold text-gray-900 dark:text-white">
                      {user?.is_admin ? "Admin" : "User"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Member Since</dt>
                    <dd className="text-lg font-semibold text-gray-900 dark:text-white">
                      {user?.created_at
                        ? new Date(user.created_at).toLocaleDateString()
                        : "N/A"}
                    </dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

            {/* System Status Card */}
            <Card>
              <CardHeader>
                <CardTitle>System Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">API Connection</span>
                    <span className="flex items-center text-green-600 dark:text-green-400">
                      <span className="h-2 w-2 bg-green-600 dark:bg-green-400 rounded-full mr-2"></span>
                      Online
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Authentication</span>
                    <span className="flex items-center text-green-600 dark:text-green-400">
                      <span className="h-2 w-2 bg-green-600 dark:bg-green-400 rounded-full mr-2"></span>
                      Active
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Search Service</span>
                    <span className="flex items-center text-green-600 dark:text-green-400">
                      <span className="h-2 w-2 bg-green-600 dark:bg-green-400 rounded-full mr-2"></span>
                      Ready
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Stats Card */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Stats</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {user?.is_admin && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Total Users</span>
                      <span className="text-2xl font-bold text-gray-900 dark:text-white">{users.length}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Your Role</span>
                    <Badge variant={user?.is_admin ? "default" : "secondary"}>
                      {user?.is_admin ? "Admin" : "User"}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Account Status</span>
                    <Badge variant="default" className="bg-green-600">Active</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* User Management Section - Only visible to admins */}
          {user?.is_admin && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>User Management</CardTitle>
                  <Button
                    onClick={() => setShowCreateForm(!showCreateForm)}
                    disabled={loading}
                  >
                    {showCreateForm ? "Cancel" : "+ Add New User"}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {/* Create User Form */}
                {showCreateForm && (
                  <form onSubmit={handleCreateUser} className="space-y-4 mb-6 p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800/50">
                    <h3 className="font-semibold text-lg text-gray-900 dark:text-white">Create New User</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">Username *</label>
                        <Input
                          type="text"
                          placeholder="username"
                          value={newUser.username}
                          onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                          required
                          minLength={3}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">Email</label>
                        <Input
                          type="email"
                          placeholder="user@example.com"
                          value={newUser.email}
                          onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">Password *</label>
                        <Input
                          type="password"
                          placeholder="Min 8 characters"
                          value={newUser.password}
                          onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                          required
                          minLength={8}
                        />
                      </div>
                      <div className="flex items-center space-x-2 pt-6">
                        <input
                          type="checkbox"
                          id="is_admin"
                          checked={newUser.is_admin}
                          onChange={(e) => setNewUser({ ...newUser, is_admin: e.target.checked })}
                          className="w-4 h-4 text-blue-600 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 dark:focus:ring-blue-600"
                        />
                        <label htmlFor="is_admin" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          Admin privileges
                        </label>
                      </div>
                    </div>
                    <Button type="submit" disabled={loading}>
                      {loading ? "Creating..." : "Create User"}
                    </Button>
                  </form>
                )}

                {/* Users List */}
                <div className="overflow-x-auto -mx-4 md:mx-0">
                  <div className="inline-block min-w-full align-middle">
                    <div className="overflow-hidden">
                      <table className="min-w-full">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="text-left py-3 px-4 text-gray-900 dark:text-white">Username</th>
                        <th className="text-left py-3 px-4 text-gray-900 dark:text-white">Email</th>
                        <th className="text-left py-3 px-4 text-gray-900 dark:text-white">Role</th>
                        <th className="text-left py-3 px-4 text-gray-900 dark:text-white">Status</th>
                        <th className="text-left py-3 px-4 text-gray-900 dark:text-white">Created</th>
                        <th className="text-left py-3 px-4 text-gray-900 dark:text-white">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {loading && users.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="text-center py-8 text-gray-500 dark:text-gray-400">
                            Loading users...
                          </td>
                        </tr>
                      ) : users.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="text-center py-8 text-gray-500 dark:text-gray-400">
                            No users found
                          </td>
                        </tr>
                      ) : (
                        users.map((u) => (
                          <tr key={u.id} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                            <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">{u.username}</td>
                            <td className="py-3 px-4 text-gray-700 dark:text-gray-300">{u.email || "—"}</td>
                            <td className="py-3 px-4">
                              <Badge variant={u.is_admin ? "default" : "secondary"}>
                                {u.is_admin ? "Admin" : "User"}
                              </Badge>
                            </td>
                            <td className="py-3 px-4">
                              <Badge variant={u.is_active ? "default" : "destructive"} className={u.is_active ? "bg-green-600" : ""}>
                                {u.is_active ? "Active" : "Inactive"}
                              </Badge>
                            </td>
                            <td className="py-3 px-4 text-sm text-gray-600 dark:text-gray-400">
                              {new Date(u.created_at).toLocaleDateString()}
                            </td>
                            <td className="py-3 px-4">
                              <Button
                                variant="destructive"
                                size="sm"
                                onClick={() => handleDeleteUser(u.id)}
                                disabled={loading || u.id === user?.id}
                              >
                                Delete
                              </Button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
