import type { User } from "../../types/auth";

export type UserRole = "admin" | "user" | "service";

/**
 * Check if user has admin role
 */
export function isAdmin(user: User | null): boolean {
  return user?.role === "admin";
}

/**
 * Check if user has specific role
 */
export function hasRole(user: User | null, role: UserRole): boolean {
  return user?.role === role;
}

/**
 * Check if user can access admin features
 */
export function canAccessAdmin(user: User | null): boolean {
  return isAdmin(user);
}

/**
 * Check if user can edit another user
 */
export function canEditUser(
  currentUser: User | null,
  targetUserId: string,
): boolean {
  if (!currentUser) return false;
  // Admin can edit anyone, users can only edit themselves
  return isAdmin(currentUser) || currentUser.id === targetUserId;
}
