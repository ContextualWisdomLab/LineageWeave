import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { GlobalSearch } from "./GlobalSearch";
import "../App.css";

const meta = {
  title: "Chrome/GlobalSearch",
  component: GlobalSearch,
  args: {
    searchLabel: "Search",
    inputLabel: "Search semantic evidence",
    closeLabel: "Close",
    helpText: "Search includes post text and semantic evidence.",
    open: true,
    value: "",
    onOpen: () => undefined,
    onClose: () => undefined,
    onChange: () => undefined,
    onSubmit: () => undefined,
  },
  parameters: {
    layout: "fullscreen",
  },
} satisfies Meta<typeof GlobalSearch>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Open: Story = {
  render: function OpenGlobalSearch(args) {
    const [open, setOpen] = useState(args.open);
    const [value, setValue] = useState(args.value);
    return (
      <header className="app-header">
        <h1 className="app-header-title">LineageWeave</h1>
        <div className="app-header-top-menu">
          <GlobalSearch
            {...args}
            open={open}
            value={value}
            onOpen={() => setOpen(true)}
            onClose={() => setOpen(false)}
            onChange={setValue}
            onSubmit={() => setOpen(false)}
          />
        </div>
      </header>
    );
  },
};

export const Closed: Story = {
  args: {
    open: false,
  },
};
