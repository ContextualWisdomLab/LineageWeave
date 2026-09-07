import type { Meta, StoryObj } from "@storybook/react-vite";
import { setLocale } from "../i18n";
import { ScreenTranslationGate } from "./ScreenTranslationGate";

const meta = {
  title: "Chrome/Screen translation gate",
  component: ScreenTranslationGate,
  args: { onRetry: () => undefined },
  decorators: [(Story, context) => {
    setLocale(context.parameters.locale ?? "en");
    return <Story />;
  }],
} satisfies Meta<typeof ScreenTranslationGate>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Loading: Story = { args: { state: "loading" } };
export const Retry: Story = { args: { state: "retry" } };
export const RetryMobile: Story = {
  args: { state: "retry" },
  parameters: { viewport: { defaultViewport: "mobile1" } },
};

export const RetryKorean: Story = { args: { state: "retry" }, parameters: { locale: "ko" } };
export const RetryJapanese: Story = { args: { state: "retry" }, parameters: { locale: "ja" } };
export const RetryChinese: Story = { args: { state: "retry" }, parameters: { locale: "zh" } };
export const RetryVietnamese: Story = { args: { state: "retry" }, parameters: { locale: "vi" } };
export const RetrySpanish: Story = { args: { state: "retry" }, parameters: { locale: "es" } };
export const RetryGerman: Story = { args: { state: "retry" }, parameters: { locale: "de" } };
export const RetryFrench: Story = { args: { state: "retry" }, parameters: { locale: "fr" } };
