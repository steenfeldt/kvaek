<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import CityPicker from "../components/CityPicker.vue";
import FieldHint from "../components/FieldHint.vue";
import NichePicker from "../components/NichePicker.vue";
import { api } from "../lib/api";
import { findCityByName, type CityOption } from "../lib/cities";
import { useSession } from "../stores/session";

const route = useRoute();
const router = useRouter();
const session = useSession();

const intent = (route.query.role as string) || sessionStorage.getItem("signup-intent") || "";
const role = ref<"creator" | "brand" | "">(intent === "creator" || intent === "brand" ? intent : "");
const error = ref("");
const busy = ref(false);

const creator = ref({ display_name: "", bio: "" });
const creatorCity = ref<CityOption | null>(null);
const selectedNiches = ref<string[]>([]);
const instagram = ref({ handle: "", follower_count: 0 });
const tiktok = ref({ handle: "", follower_count: 0 });
const acceptTerms = ref(false);

const brand = ref({ company_name: "", cvr: "", website: "" });
const brandCity = ref<CityOption | null>(null);

async function cvrLookup() {
  if (!/^\d{8}$/.test(brand.value.cvr)) return;
  try {
    const res = await fetch(`https://cvrapi.dk/api?country=dk&vat=${brand.value.cvr}`);
    if (res.ok) {
      const data = await res.json();
      if (data.name) brand.value.company_name = data.name;
      if (data.city) brandCity.value = await findCityByName(data.city);
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
        body: JSON.stringify({
          ...creator.value,
          city_id: creatorCity.value?.id ?? null,
          social_links,
          niches: selectedNiches.value,
          accept_terms: acceptTerms.value,
        }),
      });
    } else {
      await api("/onboarding/brand", {
        method: "POST",
        body: JSON.stringify({ ...brand.value, city_id: brandCity.value?.id ?? null, accept_terms: acceptTerms.value }),
      });
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
  <main class="mx-auto flex max-w-md flex-col gap-6 px-6 pt-12 pb-10 sm:pt-16">
    <UAlert v-if="session.me?.is_staff" color="info" variant="outline" class="bg-white">
      <template #description>
        {{ $t("onboarding.staffNote") }}
        <a href="/admin/" class="font-medium underline">{{ $t("onboarding.staffLink") }}</a>
      </template>
    </UAlert>
    <template v-if="!role">
      <h1 class="text-2xl font-semibold">{{ $t("onboarding.choose") }}</h1>
      <div class="grid gap-3">
        <button class="rounded-xl border-2 border-clay-200 bg-white p-4 text-left hover:border-sage-500" @click="role = 'creator'">
          {{ $t("onboarding.creator") }}
        </button>
        <button class="rounded-xl border-2 border-clay-200 bg-white p-4 text-left hover:border-sage-500" @click="role = 'brand'">
          {{ $t("onboarding.brand") }}
        </button>
      </div>
    </template>

    <form v-else-if="role === 'creator'" class="surface flex flex-col gap-4" @submit.prevent="submit">
      <h1 class="text-2xl font-semibold">{{ $t("onboarding.creator") }}</h1>
      <UFormField :label="$t('onboarding.displayName')" required>
        <UInput v-model="creator.display_name" required class="w-full" />
      </UFormField>
      <UFormField :label="$t('onboarding.city')">
        <template #hint><FieldHint :text="$t('onboarding.cityHint')" /></template>
        <CityPicker v-model="creatorCity" />
      </UFormField>
      <UFormField :label="$t('onboarding.bio')">
        <template #hint><FieldHint :text="$t('onboarding.bioHint')" /></template>
        <UTextarea v-model="creator.bio" :rows="3" class="w-full" />
      </UFormField>
      <div class="flex gap-2">
        <UInput v-model="instagram.handle" placeholder="Instagram @" class="flex-1" />
        <UInput v-model.number="instagram.follower_count" type="number" min="0" :placeholder="$t('profile.followers')" class="w-32" />
      </div>
      <div class="flex gap-2">
        <UInput v-model="tiktok.handle" placeholder="TikTok @" class="flex-1" />
        <UInput v-model.number="tiktok.follower_count" type="number" min="0" :placeholder="$t('profile.followers')" class="w-32" />
      </div>
      <UFormField :label="$t('onboarding.niches')">
        <template #hint><FieldHint :text="$t('onboarding.nichesHint')" /></template>
        <NichePicker v-model="selectedNiches" />
      </UFormField>
      <label class="flex items-start gap-2 text-sm text-ink-600">
        <input v-model="acceptTerms" type="checkbox" required class="mt-1" />
        <span>
          {{ $t("onboarding.acceptTerms") }}
          <RouterLink to="/terms" target="_blank" class="underline">{{ $t("onboarding.termsLink") }}</RouterLink>
          {{ $t("onboarding.and") }}
          <RouterLink to="/privacy" target="_blank" class="underline">{{ $t("onboarding.privacyLink") }}</RouterLink>
        </span>
      </label>
      <UButton type="submit" :loading="busy" size="xl" block :disabled="!acceptTerms">
        {{ $t("onboarding.submit") }}
      </UButton>
    </form>

    <form v-else class="surface flex flex-col gap-4" @submit.prevent="submit">
      <h1 class="text-2xl font-semibold">{{ $t("onboarding.brand") }}</h1>
      <UFormField :label="$t('onboarding.cvr')" required>
        <div class="flex gap-2">
          <UInput v-model="brand.cvr" maxlength="8" required pattern="\d{8}" class="flex-1" @blur="cvrLookup" />
          <UButton variant="outline" color="neutral" @click="cvrLookup">{{ $t("onboarding.cvrLookup") }}</UButton>
        </div>
      </UFormField>
      <UFormField :label="$t('onboarding.companyName')" required>
        <UInput v-model="brand.company_name" required class="w-full" />
      </UFormField>
      <UFormField :label="$t('onboarding.website')">
        <UInput v-model="brand.website" type="url" class="w-full" />
      </UFormField>
      <UFormField :label="$t('onboarding.city')">
        <CityPicker v-model="brandCity" />
      </UFormField>
      <label class="flex items-start gap-2 text-sm text-ink-600">
        <input v-model="acceptTerms" type="checkbox" required class="mt-1" />
        <span>
          {{ $t("onboarding.acceptTerms") }}
          <RouterLink to="/terms" target="_blank" class="underline">{{ $t("onboarding.termsLink") }}</RouterLink>
          {{ $t("onboarding.and") }}
          <RouterLink to="/privacy" target="_blank" class="underline">{{ $t("onboarding.privacyLink") }}</RouterLink>
        </span>
      </label>
      <UButton type="submit" :loading="busy" size="xl" block :disabled="!acceptTerms">
        {{ $t("onboarding.submit") }}
      </UButton>
    </form>

    <UAlert v-if="error" color="error" variant="outline" class="bg-white" :description="error" />
  </main>
</template>
