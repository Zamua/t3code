import type {
  EnvironmentProject,
  EnvironmentThreadShell,
} from "@t3tools/client-runtime/state/shell";
import { EnvironmentId, ThreadId } from "@t3tools/contracts";
import { useNavigation, useNavigationState } from "@react-navigation/native";

import { scopedThreadKey } from "../../../lib/scopedEntities";
import { uuidv4 } from "../../../lib/uuid";
import { usePendingTaskListActions } from "../../home/usePendingTaskListActions";
import type { PendingNewTask } from "../../../state/use-pending-new-tasks";
import type { ThreadPrPresentation } from "../../../state/thread-pr-presentation";
import { useAdaptiveWorkspaceLayout } from "../adaptive-workspace-context";
import { openSettings } from "../../settings/settings-navigation";
import { ThreadNavigationSidebar } from "../../threads/ThreadNavigationSidebar";
import { useOpenThreadPullRequests } from "../../threads/use-open-thread-pull-requests";
import { useSelectWorkspaceDetail } from "./useSelectWorkspaceDetail";

type Route = { readonly name: string; readonly params?: object };

function selectedThreadKey(state: { readonly index: number; readonly routes: readonly Route[] }) {
  const params = state.routes
    .slice(0, state.index + 1)
    .findLast((route) => route.name.startsWith("Thread"))?.params;
  if (
    !params ||
    !("environmentId" in params) ||
    !("threadId" in params) ||
    typeof params.environmentId !== "string" ||
    typeof params.threadId !== "string"
  ) {
    return null;
  }
  try {
    return scopedThreadKey(
      EnvironmentId.make(params.environmentId),
      ThreadId.make(params.threadId),
    );
  } catch {
    return null;
  }
}

/** The thread list in the workspace's sidebar column. */
export function WorkspaceThreadSidebar(
  props: {
    readonly width?: number;
    readonly visible?: boolean;
    readonly onRequestVisibility?: () => void;
    /** Called before a navigation so a compact drawer can close itself. */
    readonly onWillNavigate?: () => void;
  } = {},
) {
  const navigation = useNavigation();
  const {
    layout,
    panes,
    primarySidebarSearchQuery,
    setPrimarySidebarSearchQuery,
    revealPrimarySidebar,
    openWorkspaceTab,
  } = useAdaptiveWorkspaceLayout();
  const selectDetail = useSelectWorkspaceDetail();
  const openThreadPullRequests = useOpenThreadPullRequests();
  const selectedThread = useNavigationState(selectedThreadKey);
  const { onWillNavigate } = props;
  const selectThreadRoute = (params: ReactNavigation.RootParamList["Thread"]) => {
    onWillNavigate?.();
    selectDetail({ name: "Thread", params });
  };
  const { openPendingTask } = usePendingTaskListActions(selectThreadRoute);
  const openSettingsTab = () => {
    onWillNavigate?.();
    openWorkspaceTab("settings");
  };
  const openEnvironmentSettings = () => {
    onWillNavigate?.();
    openSettings(navigation, "SettingsEnvironments");
  };
  const openPendingTaskAndDismiss = (pendingTask: PendingNewTask) => {
    onWillNavigate?.();
    openPendingTask(pendingTask);
  };
  const openPullRequestsAndDismiss = (thread: EnvironmentThreadShell, pr: ThreadPrPresentation) => {
    onWillNavigate?.();
    openThreadPullRequests(thread, pr);
  };
  return (
    <ThreadNavigationSidebar
      width={props.width ?? layout.listPaneWidth ?? 0}
      visible={props.visible ?? panes.primarySidebarVisible}
      onRequestVisibility={props.onRequestVisibility ?? revealPrimarySidebar}
      selectedThreadKey={selectedThread}
      onOpenSettings={openSettingsTab}
      onOpenEnvironmentSettings={openEnvironmentSettings}
      onNewThreadInProject={(project: EnvironmentProject) =>
        selectThreadRoute({
          draft: {
            requestId: uuidv4(),
            environmentId: String(project.environmentId),
            projectId: String(project.id),
            title: project.title,
          },
        })
      }
      onNewThreadOnBranch={(thread: EnvironmentThreadShell) =>
        selectThreadRoute({
          draft: {
            requestId: uuidv4(),
            environmentId: String(thread.environmentId),
            projectId: String(thread.projectId),
            branch: thread.branch,
            worktreePath: thread.worktreePath,
          },
        })
      }
      onOpenPendingTask={openPendingTaskAndDismiss}
      onSelectThread={(thread) =>
        selectThreadRoute({
          environmentId: String(thread.environmentId),
          threadId: String(thread.id),
        })
      }
      onOpenThreadPullRequests={openPullRequestsAndDismiss}
      onSearchQueryChange={setPrimarySidebarSearchQuery}
      searchQuery={primarySidebarSearchQuery}
    />
  );
}
