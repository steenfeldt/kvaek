<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { PLATFORMS, platformInfo, type Channel, type ChannelStatus } from "../lib/platforms";

// One row per channel; "add" offers the platforms not yet used. On the profile
// page each row also shows its verification state and a verify action.
const model = defineModel<Channel[]>({ required: true });
const props = defineProps<{ statuses?: Record<string, ChannelStatus> }>();
const emit = defineEmits<{ verify: [platform: string, file: File] }>();

function status(platform: string): ChannelStatus | undefined {
  return props.statuses?.[platform];
}

// When we have pulled a number from the platform, that is what brands see;
// say so under the row instead of leaving the creator with their own guess.
const { t, locale } = useI18n();
function liveLabel(s: ChannelStatus): string {
  const date = s.synced_at
    ? new Date(s.synced_at).toLocaleDateString(locale.value === "da" ? "da-DK" : "en-GB", { day: "numeric", month: "short" })
    : "";
  const count = `${s.approximate ? t("deck.approx") + " " : ""}${s.followers.toLocaleString("da-DK")}`;
  return t("channels.liveCount", { count, date });
}
function onEvidence(platform: string, event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file) emit("verify", platform, file);
  input.value = "";
}

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
    <div v-for="(channel, i) in model" :key="channel.platform" class="flex flex-col gap-1">
    <div class="flex items-center gap-2">
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
      <template v-if="statuses && status(channel.platform)">
        <UBadge v-if="status(channel.platform)!.state === 'verified'" color="success" variant="subtle" :title="$t('channels.verifiedBadge')">
          ✔
        </UBadge>
        <UBadge v-else-if="status(channel.platform)!.state === 'stale'" color="neutral" variant="subtle" :title="$t('channels.staleBadge')">
          ✔
        </UBadge>
        <UBadge v-else-if="status(channel.platform)!.verification_status === 'pending'" color="info" variant="subtle" :title="$t('channels.pendingBadge')">
          <UIcon name="i-lucide-clock" class="size-3.5" />
        </UBadge>
        <label v-else :title="status(channel.platform)!.verification_status === 'rejected' ? $t('channels.rejectedBadge') : ''">
          <input type="file" accept="image/*" class="hidden" @change="onEvidence(channel.platform, $event)" />
          <UButton as="span" size="xs" variant="outline" :color="status(channel.platform)!.verification_status === 'rejected' ? 'warning' : 'neutral'" class="cursor-pointer bg-white">
            {{ $t("channels.verify") }}
          </UButton>
        </label>
      </template>
      <UButton
        icon="i-lucide-x"
        variant="ghost"
        color="neutral"
        :aria-label="$t('channels.remove')"
        @click="remove(i)"
      />
    </div>
    <p v-if="status(channel.platform)?.source === 'live'" class="pl-7 text-xs text-ink-600">
      {{ liveLabel(status(channel.platform)!) }}
    </p>
    </div>
    <p v-if="!model.length" class="text-sm text-ink-600">{{ $t("channels.empty") }}</p>
    <UDropdownMenu v-if="addItems.length" :items="addItems">
      <UButton icon="i-lucide-plus" variant="outline" color="neutral" class="self-start bg-white">
        {{ $t("channels.add") }}
      </UButton>
    </UDropdownMenu>
  </div>
</template>
