import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setLocale } from "../i18n";
import { ScreenTranslationGate } from "./ScreenTranslationGate";

afterEach(() => {
  setLocale("en");
});

describe("ScreenTranslationGate", () => {
  it("announces loading without exposing untranslated screen content", () => {
    render(<ScreenTranslationGate state="loading" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading this screen");
  });

  it("keeps an unclassified projection failure cause-neutral", () => {
    render(<ScreenTranslationGate state="retry" onRetry={() => undefined} />);
    expect(screen.getByText("We could not load this screen in your selected language.")).toBeInTheDocument();
    expect(screen.getByText("Retry the translation request. If it still fails, ask an administrator to check access and publication status.")).toBeInTheDocument();
    expect(screen.queryByText(/not available in your selected language yet/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/ask an administrator to publish this screen/i)).not.toBeInTheDocument();
  });

  it("offers one retry action when the selected-language screen cannot be loaded", () => {
    const onRetry = vi.fn();
    render(<ScreenTranslationGate state="retry" onRetry={onRetry} />);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it.each([
    ["ko", "선택한 언어로 이 화면을 불러오는 중입니다...", "선택한 언어로 이 화면을 불러오지 못했습니다.", "다시 시도"],
    ["en", "Loading this screen in your selected language...", "We could not load this screen in your selected language.", "Retry"],
    ["ja", "選択した言語でこの画面を読み込んでいます...", "選択した言語でこの画面を読み込めませんでした。", "再試行"],
    ["zh", "正在以所选语言加载此页面...", "无法以所选语言加载此页面。", "重试"],
    ["vi", "Đang tải màn hình này bằng ngôn ngữ đã chọn...", "Không thể tải màn hình này bằng ngôn ngữ đã chọn.", "Thử lại"],
    ["es", "Cargando esta pantalla en el idioma seleccionado...", "No se pudo cargar esta pantalla en el idioma seleccionado.", "Reintentar"],
    ["de", "Dieser Bildschirm wird in der ausgewählten Sprache geladen...", "Dieser Bildschirm konnte in der ausgewählten Sprache nicht geladen werden.", "Erneut versuchen"],
    ["fr", "Chargement de cet écran dans la langue sélectionnée…", "Impossible de charger cet écran dans la langue sélectionnée.", "Réessayer"],
  ] as const)("keeps the bootstrap loading and retry shell in %s", (locale, loading, failure, retry) => {
    setLocale(locale);
    const { rerender } = render(<ScreenTranslationGate state="loading" />);
    expect(screen.getByRole("status")).toHaveTextContent(loading);

    rerender(<ScreenTranslationGate state="retry" onRetry={() => undefined} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(failure);
    expect(screen.getByRole("button", { name: retry })).toBeInTheDocument();
  });
});
