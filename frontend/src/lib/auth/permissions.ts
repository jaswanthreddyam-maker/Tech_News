import { User } from "@/store/useStore";

export const PERMISSIONS = {
  READ_ARTICLES: "read_articles",
  SAVE_BOOKMARKS: "save_bookmarks",
  MANAGE_PROFILE: "manage_profile",
  REVIEW_ARTICLES: "review_articles",
  APPROVE_ARTICLES: "approve_articles",
  REJECT_ARTICLES: "reject_articles",
  EDIT_ARTICLE_CONTENT: "edit_article_content",
  MANAGE_SOURCES: "manage_sources",
  FORCE_CRAWL: "force_crawl",
  MANAGE_TRENDS: "manage_trends",
  VIEW_TELEMETRY: "view_telemetry",
  MANAGE_USERS: "manage_users",
  PROMOTE_USERS: "promote_users",
  VIEW_AUDIT_LOGS: "view_audit_logs",
  MANAGE_AI_QUEUE: "manage_ai_queue",
  MANAGE_FEATURE_FLAGS: "manage_feature_flags",
  EMERGENCY_CONTROLS: "emergency_controls",
  MANAGE_NOTIFICATIONS: "manage_notifications",
  FULL_ADMIN: "full_admin",
} as const;

export function hasPermission(user: User | null, permission: string): boolean {
  if (!user) return false;
  if (user.role === "super_admin") return true;
  return user.permissions?.includes(permission) ?? false;
}

export function hasAnyPermission(user: User | null, permissions: string[]): boolean {
  if (!user) return false;
  if (user.role === "super_admin") return true;
  return permissions.some((p) => user.permissions?.includes(p));
}

export function hasAllPermissions(user: User | null, permissions: string[]): boolean {
  if (!user) return false;
  if (user.role === "super_admin") return true;
  return permissions.every((p) => user.permissions?.includes(p));
}

export const ADMIN_PERMISSIONS = [
  PERMISSIONS.REVIEW_ARTICLES,
  PERMISSIONS.MANAGE_SOURCES,
  PERMISSIONS.MANAGE_TRENDS,
  PERMISSIONS.VIEW_TELEMETRY,
  PERMISSIONS.MANAGE_USERS,
  PERMISSIONS.VIEW_AUDIT_LOGS,
  PERMISSIONS.MANAGE_AI_QUEUE,
  PERMISSIONS.MANAGE_NOTIFICATIONS,
  PERMISSIONS.MANAGE_FEATURE_FLAGS,
  PERMISSIONS.EMERGENCY_CONTROLS,
  PERMISSIONS.FULL_ADMIN,
];

export function canAccessAdmin(user: User | null): boolean {
  return hasAnyPermission(user, ADMIN_PERMISSIONS);
}

export function canManageUsers(user: User | null): boolean {
  return hasPermission(user, PERMISSIONS.MANAGE_USERS);
}

export function canPromoteUsers(user: User | null): boolean {
  return hasPermission(user, PERMISSIONS.PROMOTE_USERS);
}

export function canViewTelemetry(user: User | null): boolean {
  return hasPermission(user, PERMISSIONS.VIEW_TELEMETRY);
}

export function canManageSources(user: User | null): boolean {
  return hasPermission(user, PERMISSIONS.MANAGE_SOURCES);
}

export function canReviewArticles(user: User | null): boolean {
  return hasPermission(user, PERMISSIONS.REVIEW_ARTICLES);
}

export function canManageFeatureFlags(user: User | null): boolean {
  return hasPermission(user, PERMISSIONS.MANAGE_FEATURE_FLAGS);
}

export function isSuperAdmin(user: User | null): boolean {
  return user?.role === "super_admin";
}

export function canModifyUserStatus(
  actingUser: User | null,
  targetUser: { role: string | null }
): boolean {
  if (!actingUser) return false;
  if (isSuperAdmin(actingUser)) return true;
  if (!canManageUsers(actingUser)) return false;
  if (targetUser.role === "super_admin") return false;
  if (targetUser.role === "admin" && actingUser.role === "admin") return false;
  return true;
}
