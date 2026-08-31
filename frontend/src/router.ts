import { createRouter, createWebHistory } from "vue-router";
import { useSession } from "./stores/session";

const routes = [
  { path: "/", component: () => import("./pages/Landing.vue") },
  { path: "/brands", component: () => import("./pages/BrandLanding.vue") },
  { path: "/creators", component: () => import("./pages/CreatorLanding.vue") },
  { path: "/auth", component: () => import("./pages/Auth.vue") },
  { path: "/auth/password-reset/:key", component: () => import("./pages/PasswordReset.vue") },
  { path: "/account", component: () => import("./pages/Account.vue"), meta: { auth: true } },
  { path: "/terms", component: () => import("./pages/Terms.vue") },
  { path: "/privacy", component: () => import("./pages/Privacy.vue") },
  { path: "/onboarding", component: () => import("./pages/Onboarding.vue"), meta: { auth: true } },
  {
    path: "/dashboard",
    component: () => import("./pages/Dashboard.vue"),
    meta: { auth: true, role: "brand" },
  },
  { path: "/deck", component: () => import("./pages/Deck.vue"), meta: { auth: true, role: "brand" } },
  { path: "/campaigns", component: () => import("./pages/Campaigns.vue"), meta: { auth: true, role: "brand" } },
  {
    path: "/campaigns/:id",
    component: () => import("./pages/CampaignDetail.vue"),
    meta: { auth: true, role: "brand" },
  },
  {
    path: "/campaigns/:id/payment-return",
    component: () => import("./pages/PaymentReturn.vue"),
    meta: { auth: true, role: "brand" },
  },
  { path: "/home", component: () => import("./pages/CreatorHome.vue"), meta: { auth: true, role: "creator" } },
  { path: "/profile", component: () => import("./pages/Profile.vue"), meta: { auth: true, role: "creator" } },
  { path: "/briefs", component: () => import("./pages/Briefs.vue"), meta: { auth: true } },
  { path: "/briefs/:id", component: () => import("./pages/BriefDetail.vue"), meta: { auth: true } },
  { path: "/deals", component: () => import("./pages/Deals.vue"), meta: { auth: true } },
  { path: "/deals/:id", component: () => import("./pages/DealChat.vue"), meta: { auth: true } },
];

export const router = createRouter({ history: createWebHistory(), routes });

router.beforeEach(async (to) => {
  const session = useSession();
  if (!session.loaded) {
    try {
      await session.refresh();
    } catch {
      session.loaded = true;
    }
  }
  if (to.meta.auth && !session.authenticated) return "/auth";
  if (to.meta.auth && !session.role && to.path !== "/onboarding") return "/onboarding";
  if (to.meta.role && session.role && session.role !== to.meta.role) return session.postLoginRoute();
  // Authenticated users don't need the landing/auth pages.
  if (["/", "/brands", "/creators", "/auth"].includes(to.path) && session.authenticated)
    return session.postLoginRoute();
});
