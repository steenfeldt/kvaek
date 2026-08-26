<script setup lang="ts">
import { useMutation } from "@tanstack/vue-query";
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { api } from "../lib/api";

const props = defineProps<{ creatorId?: number; dealId?: number }>();

const { t } = useI18n();
const toast = useToast();
const open = ref(false);
const reason = ref("");

const mutation = useMutation({
  mutationFn: () =>
    api("/reports", {
      method: "POST",
      body: JSON.stringify({ reason: reason.value, creator_id: props.creatorId, deal_id: props.dealId }),
    }),
  onSuccess: () => {
    open.value = false;
    reason.value = "";
    toast.add({ title: t("report.sent"), color: "success" });
  },
  onError: (e) => toast.add({ title: e.message, color: "error" }),
});
</script>

<template>
  <UModal v-model:open="open" :title="$t('report.title')">
    <UButton icon="i-lucide-flag" variant="ghost" color="neutral" size="sm" :aria-label="$t('report.button')" />
    <template #body>
      <form class="flex flex-col gap-3" @submit.prevent="mutation.mutate()">
        <UTextarea v-model="reason" :placeholder="$t('report.reason')" :rows="3" required autofocus class="w-full" />
        <UButton type="submit" color="error" :loading="mutation.isPending.value" :disabled="!reason.trim()" block>
          {{ $t("report.submit") }}
        </UButton>
      </form>
    </template>
  </UModal>
</template>
