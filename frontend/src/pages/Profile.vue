<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { ref, watch } from "vue";
import CityPicker from "../components/CityPicker.vue";
import FieldHint from "../components/FieldHint.vue";
import NichePicker from "../components/NichePicker.vue";
import { api, apiUpload } from "../lib/api";
import { cityFromProfile, type CityOption } from "../lib/cities";

interface Photo {
  id: number;
  url: string;
}
interface Profile {
  display_name: string;
  city: string;
  city_id: number | null;
  bio: string;
  listed: boolean;
  verified: boolean;
  verification_status: string | null;
  niches: { name: string; slug: string }[];
  social_links: { platform: string; handle: string; follower_count: number; verified: boolean }[];
  photos: Photo[];
}

const queryClient = useQueryClient();
const toast = useToast();
const { data: profile } = useQuery({ queryKey: ["my-profile"], queryFn: () => api<Profile>("/me/profile") });

const PLATFORMS = ["instagram", "tiktok"] as const;
const PLATFORM_LABEL: Record<(typeof PLATFORMS)[number], string> = { instagram: "Instagram", tiktok: "TikTok" };

function emptyChannels() {
  return Object.fromEntries(PLATFORMS.map((p) => [p, { handle: "", follower_count: 0 }])) as Record<
    (typeof PLATFORMS)[number],
    { handle: string; follower_count: number }
  >;
}

const form = ref({ display_name: "", city: null as CityOption | null, bio: "", niches: [] as string[] });
// One row per platform; clearing the handle removes the channel on save.
const channels = ref(emptyChannels());
watch(
  profile,
  (p) => {
    if (!p) return;
    form.value = {
      display_name: p.display_name,
      city: cityFromProfile(p),
      bio: p.bio,
      niches: p.niches.map((n) => n.slug),
    };
    channels.value = emptyChannels();
    for (const s of p.social_links) {
      if (s.platform in channels.value)
        channels.value[s.platform as (typeof PLATFORMS)[number]] = { handle: s.handle, follower_count: s.follower_count };
    }
  },
  { immediate: true },
);

const saveMutation = useMutation({
  mutationFn: () =>
    api<Profile>("/me/profile", {
      method: "PATCH",
      body: JSON.stringify({
        ...form.value,
        city: undefined,
        city_id: form.value.city?.id ?? null,
        social_links: PLATFORMS.map((platform) => ({ platform, ...channels.value[platform] })),
      }),
    }),
  onSuccess: (data) => {
    queryClient.setQueryData(["my-profile"], data);
    toast.add({ title: "✓", color: "success" });
  },
  onError: (e) => toast.add({ title: (e as Error).message, color: "error" }),
});

const fileInput = ref<HTMLInputElement | null>(null);

const uploadMutation = useMutation({
  mutationFn: (file: File) => apiUpload<Photo>("/me/photos", file),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ["my-profile"] }),
  onError: (e) => toast.add({ title: (e as Error).message, color: "error" }),
});

function onFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (file) uploadMutation.mutate(file);
  if (fileInput.value) fileInput.value.value = "";
}

const deleteMutation = useMutation({
  mutationFn: (photoId: number) => api(`/me/photos/${photoId}`, { method: "DELETE" }),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ["my-profile"] }),
});

const evidenceInput = ref<HTMLInputElement | null>(null);

const verifyMutation = useMutation({
  mutationFn: (file: File) => apiUpload("/me/verification", file),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ["my-profile"] }),
  onError: (e) => toast.add({ title: (e as Error).message, color: "error" }),
});

function onEvidence(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (file) verifyMutation.mutate(file);
  if (evidenceInput.value) evidenceInput.value.value = "";
}
</script>

<template>
  <main v-if="profile" class="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
    <header class="flex items-center justify-between">
      <h1 class="text-xl font-semibold">{{ $t("profile.title") }}</h1>
      <div class="flex gap-2">
        <UBadge v-if="profile.verified" color="success" variant="subtle">✔ {{ $t("profile.verified") }}</UBadge>
        <UBadge :color="profile.listed ? 'success' : 'neutral'" variant="subtle">
          {{ profile.listed ? $t("profile.listed") : $t("profile.notListed") }}
        </UBadge>
      </div>
    </header>

    <UCard>
      <h2 class="mb-3 font-semibold">{{ $t("profile.photos") }}</h2>
      <div class="grid grid-cols-3 gap-3">
        <div v-for="p in profile.photos" :key="p.id" class="group relative aspect-square">
          <img :src="p.url" class="h-full w-full rounded-xl object-cover" alt="" />
          <UButton
            icon="i-lucide-x"
            color="neutral"
            size="xs"
            class="absolute top-1 right-1 hidden group-hover:flex"
            @click="deleteMutation.mutate(p.id)"
          />
        </div>
        <label
          v-if="profile.photos.length < 6"
          class="flex aspect-square cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-clay-200 text-ink-600 hover:border-sage-500"
        >
          <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFile" />
          <span v-if="uploadMutation.isPending.value">…</span>
          <span v-else>+ {{ $t("profile.addPhoto") }}</span>
        </label>
      </div>
    </UCard>

    <UCard>
      <form class="flex flex-col gap-4" @submit.prevent="saveMutation.mutate()">
        <UFormField :label="$t('onboarding.displayName')" required>
          <UInput v-model="form.display_name" required class="w-full" />
        </UFormField>
        <UFormField :label="$t('onboarding.city')">
          <template #hint><FieldHint :text="$t('onboarding.cityHint')" /></template>
          <CityPicker v-model="form.city" />
        </UFormField>
        <UFormField :label="$t('onboarding.bio')">
          <template #hint><FieldHint :text="$t('onboarding.bioHint')" /></template>
          <UTextarea v-model="form.bio" :rows="3" class="w-full" />
        </UFormField>
        <UFormField :label="$t('onboarding.niches')">
          <template #hint><FieldHint :text="$t('onboarding.nichesHint')" /></template>
          <NichePicker v-model="form.niches" />
        </UFormField>
        <UFormField :label="$t('profile.channels')">
          <template #hint><FieldHint :text="$t('profile.channelsHint')" /></template>
          <div class="flex flex-col gap-2">
            <div v-for="platform in PLATFORMS" :key="platform" class="flex items-center gap-2">
              <UInput v-model="channels[platform].handle" :placeholder="`${PLATFORM_LABEL[platform]} @`" class="flex-1" />
              <UInput
                v-model.number="channels[platform].follower_count"
                type="number"
                min="0"
                :placeholder="$t('profile.followers')"
                class="w-32"
              />
              <UBadge
                v-if="profile.social_links.find((s) => s.platform === platform)?.verified"
                color="success"
                variant="subtle"
              >
                ✔
              </UBadge>
            </div>
          </div>
        </UFormField>
        <UButton type="submit" :loading="saveMutation.isPending.value" block>
          {{ $t("profile.save") }}
        </UButton>
      </form>
    </UCard>

    <UCard v-if="!profile.verified">
      <h2 class="mb-1 font-semibold">{{ $t("profile.verifyTitle") }}</h2>
      <template v-if="profile.verification_status === 'pending'">
        <UAlert color="info" variant="subtle" :description="$t('profile.verifyPending')" />
      </template>
      <template v-else>
        <p class="mb-3 text-sm text-ink-600">{{ $t("profile.verifyHint") }}</p>
        <UAlert
          v-if="profile.verification_status === 'rejected'"
          color="warning"
          variant="subtle"
          :description="$t('profile.verifyRejected')"
          class="mb-3"
        />
        <label>
          <input ref="evidenceInput" type="file" accept="image/*" class="hidden" @change="onEvidence" />
          <UButton as="span" variant="outline" :loading="verifyMutation.isPending.value" class="cursor-pointer">
            {{ $t("profile.verifyCta") }}
          </UButton>
        </label>
      </template>
    </UCard>
  </main>
</template>
