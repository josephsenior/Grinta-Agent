import type { User } from "#/types/auth";

export interface UserFilters {
  searchQuery: string;
  roleFilter: string;
  statusFilter: string;
}

function matchesSearchQuery(user: User, query: string): boolean {
  const lowerQuery = query.toLowerCase();
  return (
    user.email.toLowerCase().includes(lowerQuery) ||
    user.username?.toLowerCase().includes(lowerQuery) ||
    user.id.toLowerCase().includes(lowerQuery)
  );
}

function matchesRoleFilter(user: User, roleFilter: string): boolean {
  return roleFilter === "all" || user.role === roleFilter;
}

function matchesStatusFilter(user: User, statusFilter: string): boolean {
  if (statusFilter === "active") {
    return user.is_active;
  }
  if (statusFilter === "inactive") {
    return !user.is_active;
  }
  return true;
}

export function filterUsers(users: User[], filters: UserFilters): User[] {
  return users.filter((user) => {
    if (filters.searchQuery && !matchesSearchQuery(user, filters.searchQuery)) {
      return false;
    }

    if (!matchesRoleFilter(user, filters.roleFilter)) {
      return false;
    }

    if (!matchesStatusFilter(user, filters.statusFilter)) {
      return false;
    }

    return true;
  });
}
