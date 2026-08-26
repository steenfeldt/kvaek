<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { ref, watch } from "vue";
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

const queryClient = useQueryClient();
const toast = useToast();
const { data: profile } = useQuery({ queryKey: ["my-profile"], queryFn: () => api<Profile>("/me/profile") });

const form = ref({ display_name: "", city: "", bio: "" });
watch(
  profile,
  (p) => {
    if (p) form.value = { display_name: p.display_name, city: p.city, bio: p.bio };
  },
  { immediate: true },
);

const saveMutation = useMutation({
  mutationFn: () => api<Profile>("/me/profile", { method: "PATCH", body: JSON.stringify(form.value) }),
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
</script>

<template>
  <main v-if="profile" class="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
    <header class="flex items-center justify-between">
      <h1 class="text-xl font-semibold">{{ $t("profile.title") }}</h1>
      <UBadge :color="profile.listed ? 'success' : 'neutral'" variant="subtle">
        {{ profile.listed ? $t("profile.listed") : $t("profile.notListed") }}
      </UBadge>
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
          class="flex aspect-square cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-clay-200 text-ink-600 hover:border-clay-500"
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
          <UInput v-model="form.city" class="w-full" />
        </UFormField>
        <UFormField :label="$t('onboarding.bio')">
          <UTextarea v-model="form.bio" :rows="3" class="w-full" />
        </UFormField>
        <div class="flex flex-wrap gap-2">
          <UBadge v-for="s in profile.social_links" :key="s.platform" color="primary" variant="subtle">
            {{ s.platform }} @{{ s.handle }} · {{ s.follower_count.toLocaleString("da-DK") }}
          </UBadge>
        </div>
        <UButton type="submit" :loading="saveMutation.isPending.value" block>
          {{ $t("profile.save") }}
        </UButton>
      </form>
    </UCard>
  </main>
</template>
