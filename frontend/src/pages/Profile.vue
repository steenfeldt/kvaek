<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, apiUpload } from "../lib/api";

interface Photo {
  id: number;
  url: string;
}
interface Profile {
  display_name: string;
  city: string;
  bio: string;
  listed: boolean;
  verified: boolean;
  niches: string[];
  social_links: { platform: string; handle: string; follower_count: number; verified: boolean }[];
  photos: Photo[];
}

const profile = ref<Profile | null>(null);
const saved = ref(false);
const error = ref("");
const fileInput = ref<HTMLInputElement | null>(null);

onMounted(async () => {
  profile.value = await api<Profile>("/me/profile");
});

async function save() {
  if (!profile.value) return;
  error.value = "";
  const { display_name, city, bio } = profile.value;
  profile.value = await api<Profile>("/me/profile", {
    method: "PATCH",
    body: JSON.stringify({ display_name, city, bio }),
  });
  saved.value = true;
  setTimeout(() => (saved.value = false), 2000);
}

async function upload(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file || !profile.value) return;
  error.value = "";
  try {
    const photo = await apiUpload<Photo>("/me/photos", file);
    profile.value.photos.push(photo);
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    if (fileInput.value) fileInput.value.value = "";
  }
}

async function removePhoto(photoId: number) {
  if (!profile.value) return;
  await api(`/me/photos/${photoId}`, { method: "DELETE" });
  profile.value.photos = profile.value.photos.filter((p) => p.id !== photoId);
}
</script>

<template>
  <main v-if="profile" class="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
    <header class="flex items-center justify-between">
      <h1 class="text-xl font-semibold">{{ $t("profile.title") }}</h1>
      <span
        class="rounded-full px-3 py-1 text-sm"
        :class="profile.listed ? 'bg-green-100 text-green-800' : 'bg-clay-100 text-ink-600'"
      >
        {{ profile.listed ? $t("profile.listed") : $t("profile.notListed") }}
      </span>
    </header>

    <section class="rounded-2xl bg-white p-6 shadow">
      <h2 class="mb-3 font-semibold">{{ $t("profile.photos") }}</h2>
      <div class="grid grid-cols-3 gap-3">
        <div v-for="p in profile.photos" :key="p.id" class="group relative aspect-square">
          <img :src="p.url" class="h-full w-full rounded-xl object-cover" alt="" />
          <button
            class="absolute right-1 top-1 hidden rounded-full bg-black/60 px-2 py-0.5 text-sm text-white group-hover:block"
            @click="removePhoto(p.id)"
          >
            ✕
          </button>
        </div>
        <label
          v-if="profile.photos.length < 6"
          class="flex aspect-square cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-clay-200 text-ink-600 hover:border-clay-500"
        >
          <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="upload" />
          + {{ $t("profile.addPhoto") }}
        </label>
      </div>
    </section>

    <form class="flex flex-col gap-3 rounded-2xl bg-white p-6 shadow" @submit.prevent="save">
      <input v-model="profile.display_name" :placeholder="$t('onboarding.displayName')" required class="input" />
      <input v-model="profile.city" :placeholder="$t('onboarding.city')" class="input" />
      <textarea v-model="profile.bio" :placeholder="$t('onboarding.bio')" rows="3" class="input" />
      <div class="flex flex-wrap gap-2 text-sm text-ink-600">
        <span v-for="s in profile.social_links" :key="s.platform" class="rounded-full bg-clay-100 px-3 py-1">
          {{ s.platform }} @{{ s.handle }} · {{ s.follower_count.toLocaleString("da-DK") }}
        </span>
      </div>
      <button class="rounded-lg bg-clay-600 py-3 font-medium text-white hover:bg-clay-700">
        {{ saved ? $t("profile.saved") : $t("profile.save") }}
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
