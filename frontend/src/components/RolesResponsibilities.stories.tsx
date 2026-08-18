import type { Meta, StoryObj } from "@storybook/react-vite";
import { RolesResponsibilities } from "./RolesResponsibilities";

const meta = {
  title: "역할·책임/RolesResponsibilities",
  component: RolesResponsibilities,
} satisfies Meta<typeof RolesResponsibilities>;

export default meta;

type Story = StoryObj<typeof meta>;

export const SeededActors: Story = {
  args: {
    roles: [
      {
        actor_name: "Ada West",
        responsibility: "우리 측 후속",
        actor_type_code: "prov_person",
        affiliated_organization_name: "Demo Corp",
      },
      {
        actor_name: "당사",
        responsibility: "출하 일정 확정",
        actor_type_code: "prov_organization",
        affiliated_organization_name: null,
      },
      {
        actor_name: "설계팀",
        responsibility: "도면 검토",
        actor_type_code: "prov_team",
        affiliated_organization_name: "Demo Corp",
      },
    ],
  },
};

export const Empty: Story = {
  args: {
    roles: [],
  },
};
