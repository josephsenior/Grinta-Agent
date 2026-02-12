import { I18nKey } from "#/i18n/declaration";
import { DOCUMENTATION_URL } from "../constants/app";

export interface Tip {
  key: I18nKey;
  link?: string;
}

export const TIPS: Tip[] = [
  {
    key: I18nKey.TIPS$CUSTOMIZE_PLAYBOOK,
    link: DOCUMENTATION_URL.PROMPTING.PLAYBOOKS_REPO,
  },
  {
    key: I18nKey.TIPS$SETUP_SCRIPT,
    link: DOCUMENTATION_URL.PROMPTING.REPOSITORY_SETUP,
  },
  { key: I18nKey.TIPS$VSCODE_INSTANCE },
  { key: I18nKey.TIPS$SAVE_WORK },
  {
    key: I18nKey.TIPS$SPECIFY_FILES,
    link: DOCUMENTATION_URL.PROMPTING.BEST_PRACTICES,
  },
  {
    key: I18nKey.TIPS$HEADLESS_MODE,
    link: DOCUMENTATION_URL.HOW_TO.HEADLESS_MODE,
  },
  {
    key: I18nKey.TIPS$CLI_MODE,
    link: DOCUMENTATION_URL.HOW_TO.CLI_MODE,
  },
  {
    key: I18nKey.TIPS$GITHUB_HOOK,
    link: DOCUMENTATION_URL.GITHUB.INSTALLATION,
  },
  {
    key: I18nKey.TIPS$BLOG_SIGNUP,
    link: DOCUMENTATION_URL.BLOG,
  },
  {
    key: I18nKey.TIPS$API_USAGE,
    link: DOCUMENTATION_URL.HEALTH_CHECK,
  },
];

export function getRandomTip(): Tip {
  const randomIndex = Math.floor(Math.random() * TIPS.length);
  return TIPS[randomIndex];
}
