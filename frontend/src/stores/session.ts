import { defineStore } from "pinia";
import { api } from "../lib/api";

interface Me {
  authenticated: boolean;
  email?: string | null;
  role?: "creator" | "brand" | null;
  display_name?: string | null;
}

export const useSession = defineStore("session", {
  state: () => ({ me: null as Me | null, loaded: false }),
  getters: {
    authenticated: (s) => s.me?.authenticated ?? false,
    role: (s) => s.me?.role ?? null,
  },
  actions: {
    async refresh() {
      this.me = await api<Me>("/me");
      this.loaded = true;
    },
    /** The single post-login router: one place decides where a user lands. */
    postLoginRoute(intent?: string): string {
      if (!this.authenticated) return "/auth";
      if (!this.role) return intent ? `/onboarding?role=${intent}` : "/onboarding";
      return this.role === "brand" ? "/deck" : "/home";
    },
  },
});
