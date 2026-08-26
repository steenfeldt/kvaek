<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../lib/api";
import { useSession } from "../stores/session";

const route = useRoute();
const router = useRouter();
const session = useSession();

const intent = (route.query.role as string) || sessionStorage.getItem("signup-intent") || "";
const role = ref<"creator" | "brand" | "">(intent === "creator" || intent === "brand" ? intent : "");
const error = ref("");
const busy = ref(false);

const creator = ref({ invite_code: "", display_name: "", city: "", bio: "" });
const instagram = ref({ handle: "", follower_count: 0 });
const tiktok = ref({ handle: "", follower_count: 0 });

const brand = ref({ company_name: "", cvr: "", website: "", city: "" });

async function cvrLookup() {
  if (!/^\d{8}$/.test(brand.value.cvr)) return;
  try {
    const res = await fetch(`https://cvrapi.dk/api?country=dk&vat=${brand.value.cvr}`);
    if (res.ok) {
      const data = await res.json();
      if (data.name) brand.value.company_name = data.name;
      if (data.city) brand.value.city = data.city;
    }
  } catch {}
}

async function submit() {
  error.value = "";
  busy.value = true;
  try {
    if (role.value === "creator") {
      const social_links = [
        { platform: "instagram", ...instagram.value },
        { platform: "tiktok", ...tiktok.value },
      ].filter((s) => s.handle.trim());
      await api("/onboarding/creator", {
        method: "POST",
        body: JSON.stringify({ ...creator.value, social_links, niches: [] }),
      });
    } else {
      await api("/onboarding/brand", { method: "POST", body: JSON.stringify(brand.value) });
    }
    sessionStorage.removeItem("signup-intent");
    await session.refresh();
    router.push(session.postLoginRoute());
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-6 py-10">
    <template v-if="!role">
      <h1 class="text-2xl font-semibold">{{ $t("onboarding.choose") }}</h1>
      <div class="grid gap-3">
        <button class="rounded-xl border-2 border-clay-200 bg-white p-4 text-left hover:border-clay-500" @click="role = 'creator'">
          {{ $t("onboarding.creator") }}
        </button>
        <button class="rounded-xl border-2 border-clay-200 bg-white p-4 text-left hover:border-clay-500" @click="role = 'brand'">
          {{ $t("onboarding.brand") }}
        </button>
      </div>
    </template>

    <form v-else-if="role === 'creator'" class="flex flex-col gap-3" @submit.prevent="submit">
      <h1 class="text-2xl font-semibold">{{ $t("onboarding.creator") }}</h1>
      <input v-model="creator.invite_code" :placeholder="$t('onboarding.inviteCode')" required class="input" />
      <input v-model="creator.display_name" :placeholder="$t('onboarding.displayName')" required class="input" />
      <input v-model="creator.city" :placeholder="$t('onboarding.city')" class="input" />
      <textarea v-model="creator.bio" :placeholder="$t('onboarding.bio')" rows="3" class="input" />
      <div class="flex gap-2">
        <input v-model="instagram.handle" placeholder="Instagram @" class="input flex-1" />
        <input v-model.number="instagram.follower_count" type="number" min="0" placeholder="Følgere" class="input w-32" />
      </div>
      <div class="flex gap-2">
        <input v-model="tiktok.handle" placeholder="TikTok @" class="input flex-1" />
        <input v-model.number="tiktok.follower_count" type="number" min="0" placeholder="Følgere" class="input w-32" />
      </div>
      <button :disabled="busy" class="rounded-lg bg-clay-600 py-3 font-medium text-white hover:bg-clay-700">
        {{ $t("onboarding.submit") }}
      </button>
    </form>

    <form v-else class="flex flex-col gap-3" @submit.prevent="submit">
      <h1 class="text-2xl font-semibold">{{ $t("onboarding.brand") }}</h1>
      <div class="flex gap-2">
        <input v-model="brand.cvr" :placeholder="$t('onboarding.cvr')" maxlength="8" class="input flex-1" @blur="cvrLookup" />
        <button type="button" class="rounded-lg border border-clay-200 px-4" @click="cvrLookup">
          {{ $t("onboarding.cvrLookup") }}
        </button>
      </div>
      <input v-model="brand.company_name" :placeholder="$t('onboarding.companyName')" required class="input" />
      <input v-model="brand.website" :placeholder="$t('onboarding.website')" type="url" class="input" />
      <input v-model="brand.city" :placeholder="$t('onboarding.city')" class="input" />
      <button :disabled="busy" class="rounded-lg bg-clay-600 py-3 font-medium text-white hover:bg-clay-700">
        {{ $t("onboarding.submit") }}
      </button>
    </form>

    <p v-if="error" class="text-sm text-red-700">{{ error }}</p>
  </main>
</template>

<style scoped>
@reference "../style.css";
.input {
  @apply rounded-lg border border-clay-200 bg-white px-4 py-3;
}
</style>
