import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { GlobalSearch, type GlobalSearchProps } from "./GlobalSearch";

it("opens, submits, closes, and restores focus from the global search", () => {
  const props: GlobalSearchProps = {
    open: false,
    value: "project",
    searchLabel: "Search",
    inputLabel: "Search authorized posts",
    closeLabel: "Close search",
    helpText: "Enter a source-backed query.",
    onOpen: vi.fn(),
    onClose: vi.fn(),
    onChange: vi.fn(),
    onSubmit: vi.fn(),
  };
  const { rerender } = render(<GlobalSearch {...props} />);

  const trigger = screen.getByRole("button", { name: "Search" });
  fireEvent.click(trigger);
  expect(props.onOpen).toHaveBeenCalledOnce();

  rerender(<GlobalSearch {...props} open />);
  const input = screen.getByRole("searchbox", { name: props.inputLabel });
  expect(input).toHaveFocus();
  fireEvent.change(input, { target: { value: "updated" } });
  expect(props.onChange).toHaveBeenCalledWith("updated");
  fireEvent.submit(screen.getByRole("search"));
  expect(props.onSubmit).toHaveBeenCalledWith("project");

  fireEvent.keyDown(document, { key: "Enter" });
  expect(props.onClose).not.toHaveBeenCalled();
  fireEvent.keyDown(document, { key: "Escape" });
  expect(props.onClose).toHaveBeenCalledOnce();
  expect(trigger).toHaveFocus();

  fireEvent.click(screen.getByRole("button", { name: props.closeLabel }));
  expect(props.onClose).toHaveBeenCalledTimes(2);
  expect(trigger).toHaveFocus();

  rerender(<GlobalSearch {...props} />);
  fireEvent.keyDown(document, { key: "Escape" });
  expect(props.onClose).toHaveBeenCalledTimes(2);
});
