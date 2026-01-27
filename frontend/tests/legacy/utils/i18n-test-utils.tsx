import { ReactNode } from "react";
import { I18nextProvider } from "react-i18next";
import type { i18n as I18nInstance } from "i18next";

// Keep the mock shape minimal and cast to I18nInstance only when passed to the provider
const mockI18n = {
  language: "ja",
  t: (key: string) => {
    const translations: Record<string, string> = {
      SUGGESTIONS$TODO_APP: "ToDoリストアプリを開発する",
      LANDING$BUILD_APP_BUTTON: "プルリクエストを表示するアプリを開発する",
      SUGGESTIONS$HACKER_NEWS:
        "Hacker Newsのトップ記事を表示するbashスクリプトを作成する",
      LANDING$TITLE: "一緒に開発を始めましょう！",
      OPEN_IN_VSCODE: "VS Codeで開く",
      INCREASE_TEST_COVERAGE: "テストカバレッジを向上",
      AUTO_MERGE_PRS: "PRを自動マージ",
      FIX_README: "READMEを修正",
      CLEAN_DEPENDENCIES: "依存関係を整理",
    };
    return translations[key] || key;
  },
  exists: () => true,
  changeLanguage: () => Promise.resolve(),
  use: () => mockI18n,
} as unknown as I18nInstance;

export function I18nTestProvider({ children }: { children: ReactNode }) {
  return <I18nextProvider i18n={mockI18n}>{children}</I18nextProvider>;
}
