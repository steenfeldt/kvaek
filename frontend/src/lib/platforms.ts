// Keep in sync with SocialLink.Platform in backend/accounts/models.py.
export interface PlatformInfo {
  value: string;
  label: string;
  icon: string;
}

export const PLATFORMS: PlatformInfo[] = [
  { value: "instagram", label: "Instagram", icon: "simple-icons:instagram" },
  { value: "tiktok", label: "TikTok", icon: "simple-icons:tiktok" },
  { value: "youtube", label: "YouTube", icon: "simple-icons:youtube" },
  { value: "facebook", label: "Facebook", icon: "simple-icons:facebook" },
  { value: "snapchat", label: "Snapchat", icon: "simple-icons:snapchat" },
  { value: "linkedin", label: "LinkedIn", icon: "simple-icons:linkedin" },
];

export function platformInfo(value: string): PlatformInfo {
  return PLATFORMS.find((p) => p.value === value) ?? { value, label: value, icon: "lucide:link" };
}

export interface Channel {
  platform: string;
  handle: string;
  follower_count: number;
  verified?: boolean;
}
