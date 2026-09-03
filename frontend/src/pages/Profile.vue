<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import Sortable from "sortablejs";
import { onBeforeUnmount, ref, watch } from "vue";
import BioEditor from "../components/BioEditor.vue";
import ChannelEditor from "../components/ChannelEditor.vue";
import CityPicker from "../components/CityPicker.vue";
import FieldHint from "../components/FieldHint.vue";
import NichePicker from "../components/NichePicker.vue";
import { api, apiUpload } from "../lib/api";
import { cityFromProfile, type CityOption } from "../lib/cities";
import type { Channel } from "../lib/platforms";

interface Photo {
  id: number;
  url: string;
}
interface PortfolioItem {
  id: number;
  media_type: "image" | "video";
  url: string;
  title: string;
  description: string;
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
  photo: Photo | null;
  portfolio: PortfolioItem[];
}

const queryClient = useQueryClient();
const toast = useToast();
const { data: profile } = useQuery({ queryKey: ["my-profile"], queryFn: () => api<Profile>("/me/profile") });

const form = ref({ display_name: "", city: null as CityOption | null, bio: "", niches: [] as string[] });
// Channels are saved together with the rest of the form.
const channels = ref<Channel[]>([]);
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
    channels.value = p.social_links.map((s) => ({ ...s }));
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
        social_links: channels.value.filter((c) => c.handle.trim()),
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

// --- portfolio: past jobs, one image/video + text each ---
const MAX_PORTFOLIO = 12;
const addingItem = ref(false);
const newItem = ref({ title: "", description: "", file: null as File | null });
const itemFileInput = ref<HTMLInputElement | null>(null);

function onItemFile(event: Event) {
  newItem.value.file = (event.target as HTMLInputElement).files?.[0] ?? null;
}

const addItemMutation = useMutation({
  mutationFn: () =>
    apiUpload<PortfolioItem>("/me/portfolio", newItem.value.file as File, {
      title: newItem.value.title,
      description: newItem.value.description,
    }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["my-profile"] });
    newItem.value = { title: "", description: "", file: null };
    addingItem.value = false;
  },
  onError: (e) => toast.add({ title: (e as Error).message, color: "error" }),
});

const deleteItemMutation = useMutation({
  mutationFn: (id: number) => api(`/me/portfolio/${id}`, { method: "DELETE" }),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ["my-profile"] }),
});

// Drag-and-drop ordering. Sortable moves the DOM node; we move it back and
// let Vue re-render from the new order so the two never disagree.
const reorderMutation = useMutation({
  mutationFn: (ids: number[]) => api<PortfolioItem[]>("/me/portfolio/order", { method: "PUT", body: JSON.stringify({ ids }) }),
  onSuccess: (portfolio) => {
    const current = queryClient.getQueryData<Profile>(["my-profile"]);
    if (current) queryClient.setQueryData(["my-profile"], { ...current, portfolio });
  },
  onError: (e) => {
    toast.add({ title: (e as Error).message, color: "error" });
    queryClient.invalidateQueries({ queryKey: ["my-profile"] });
  },
});

const portfolioList = ref<HTMLElement | null>(null);
let sortable: Sortable | null = null;
watch(portfolioList, (el) => {
  sortable?.destroy();
  sortable = null;
  if (!el) return;
  sortable = Sortable.create(el, {
    animation: 150,
    handle: "[data-drag-handle]",
    onEnd(evt) {
      const { item, from, oldIndex, newIndex } = evt;
      if (oldIndex === undefined || newIndex === undefined || oldIndex === newIndex) return;
      from.removeChild(item);
      from.insertBefore(item, from.children[oldIndex] ?? null);
      const ids = (profile.value?.portfolio ?? []).map((p) => p.id);
      ids.splice(newIndex, 0, ids.splice(oldIndex, 1)[0]);
      const current = queryClient.getQueryData<Profile>(["my-profile"]);
      if (current) {
        const byId = new Map(current.portfolio.map((p) => [p.id, p]));
        queryClient.setQueryData(["my-profile"], { ...current, portfolio: ids.map((id) => byId.get(id)!) });
      }
      reorderMutation.mutate(ids);
    },
  });
});
onBeforeUnmount(() => sortable?.destroy());

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
      <h2 class="mb-1 font-semibold">{{ $t("profile.photo") }}</h2>
      <p class="mb-3 text-sm text-ink-600">{{ $t("profile.photoHint") }}</p>
      <div class="flex items-center gap-4">
        <img v-if="profile.photo" :src="profile.photo.url" class="h-28 w-28 rounded-xl object-cover" alt="" />
        <div v-else class="flex h-28 w-28 items-center justify-center rounded-xl bg-clay-100 text-3xl">📷</div>
        <div class="flex flex-col gap-2">
          <label>
            <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFile" />
            <UButton as="span" variant="outline" color="neutral" class="cursor-pointer bg-white" :loading="uploadMutation.isPending.value">
              {{ profile.photo ? $t("profile.replacePhoto") : $t("profile.addPhoto") }}
            </UButton>
          </label>
          <UButton
            v-if="profile.photo"
            variant="ghost"
            color="neutral"
            size="sm"
            class="self-start"
            @click="deleteMutation.mutate(profile.photo.id)"
          >
            {{ $t("profile.removePhoto") }}
          </UButton>
        </div>
      </div>
    </UCard>

    <UCard>
      <h2 class="mb-1 font-semibold">{{ $t("portfolio.title") }}</h2>
      <p class="mb-4 text-sm text-ink-600">{{ $t("portfolio.hint") }}</p>
      <ul v-if="profile.portfolio.length" ref="portfolioList" class="mb-4 grid gap-3 sm:grid-cols-2">
        <li v-for="item in profile.portfolio" :key="item.id" class="group relative overflow-hidden rounded-xl border border-clay-200 bg-white">
          <button
            type="button"
            data-drag-handle
            class="absolute top-2 left-2 flex h-7 w-7 cursor-grab touch-none items-center justify-center rounded-md bg-white/90 text-ink-600 active:cursor-grabbing"
            :aria-label="$t('portfolio.drag')"
          >
            <UIcon name="i-lucide-grip-vertical" class="size-4" />
          </button>
          <video v-if="item.media_type === 'video'" :src="item.url" class="aspect-video w-full bg-black object-cover" controls preload="metadata" />
          <img v-else :src="item.url" class="aspect-video w-full object-cover" alt="" />
          <div class="p-3">
            <p class="font-medium">{{ item.title }}</p>
            <p v-if="item.description" class="mt-1 text-sm whitespace-pre-line text-ink-600">{{ item.description }}</p>
          </div>
          <UButton
            icon="i-lucide-x"
            color="neutral"
            size="xs"
            class="absolute top-2 right-2 bg-white/90"
            :aria-label="$t('portfolio.remove')"
            @click="deleteItemMutation.mutate(item.id)"
          />
        </li>
      </ul>
      <form v-if="addingItem" class="flex flex-col gap-3 rounded-xl bg-cream p-4" @submit.prevent="addItemMutation.mutate()">
        <UFormField :label="$t('portfolio.media')" required>
          <input
            ref="itemFileInput"
            type="file"
            accept="image/*,video/mp4,video/webm,video/quicktime"
            required
            class="block w-full text-sm"
            @change="onItemFile"
          />
        </UFormField>
        <UFormField :label="$t('portfolio.itemTitle')" required>
          <UInput v-model="newItem.title" required maxlength="100" class="w-full" />
        </UFormField>
        <UFormField :label="$t('portfolio.description')">
          <UTextarea v-model="newItem.description" :rows="3" class="w-full" :placeholder="$t('portfolio.descriptionPlaceholder')" />
        </UFormField>
        <div class="flex gap-2">
          <UButton type="submit" :loading="addItemMutation.isPending.value" :disabled="!newItem.file || !newItem.title.trim()">
            {{ $t("portfolio.add") }}
          </UButton>
          <UButton variant="ghost" color="neutral" @click="addingItem = false">{{ $t("portfolio.cancel") }}</UButton>
        </div>
      </form>
      <UButton
        v-else-if="profile.portfolio.length < MAX_PORTFOLIO"
        icon="i-lucide-plus"
        variant="outline"
        color="neutral"
        class="bg-white"
        @click="addingItem = true"
      >
        {{ $t("portfolio.addJob") }}
      </UButton>
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
          <BioEditor v-model="form.bio" />
        </UFormField>
        <UFormField :label="$t('onboarding.niches')">
          <template #hint><FieldHint :text="$t('onboarding.nichesHint')" /></template>
          <NichePicker v-model="form.niches" />
        </UFormField>
        <UFormField :label="$t('profile.channels')">
          <template #hint><FieldHint :text="$t('channels.hint')" /></template>
          <ChannelEditor v-model="channels" />
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
