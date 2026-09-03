<script setup lang="ts">
import { computed } from "vue";
import { PLATFORMS, platformInfo, type Channel } from "../lib/platforms";

// One row per channel; "add" offers the platforms not yet used.
const model = defineModel<Channel[]>({ required: true });

const addItems = computed(() =>
  PLATFORMS.filter((p) => !model.value.some((c) => c.platform === p.value)).map((p) => ({
    label: p.label,
    icon: p.icon,
    onSelect: () => {
      model.value = [...model.value, { platform: p.value, handle: "", follower_count: 0 }];
    },
  })),
);

function remove(index: number) {
  model.value = model.value.filter((_, i) => i !== index);
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <div v-for="(channel, i) in model" :key="channel.platform" class="flex items-center gap-2">
      <UIcon
        :name="platformInfo(channel.platform).icon"
        class="size-5 shrink-0 text-ink-600"
        :title="platformInfo(channel.platform).label"
      />
      <UInput
        v-model="channel.handle"
        :placeholder="`${platformInfo(channel.platform).label} @`"
        required
        class="flex-1"
      />
      <UInput
        v-model.number="channel.follower_count"
        type="number"
        min="0"
        :placeholder="$t('profile.followers')"
        class="w-28"
      />
      <UBadge v-if="channel.verified" color="success" variant="subtle">✔</UBadge>
      <UButton
        icon="i-lucide-x"
        variant="ghost"
        color="neutral"
        :aria-label="$t('channels.remove')"
        @click="remove(i)"
      />
    </div>
    <p v-if="!model.length" class="text-sm text-ink-600">{{ $t("channels.empty") }}</p>
    <UDropdownMenu v-if="addItems.length" :items="addItems">
      <UButton icon="i-lucide-plus" variant="outline" color="neutral" class="self-start bg-white">
        {{ $t("channels.add") }}
      </UButton>
    </UDropdownMenu>
  </div>
</template>
