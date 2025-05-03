import {
  ThreadListItemPrimitive,
  ThreadListPrimitive,
} from "@assistant-ui/react";
import { ArchiveIcon, PlusIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { TooltipIconButton } from "@/components/tooltip-icon-button";

export const ThreadList = () => {
  return (
    (<ThreadListPrimitive.Root className="flex flex-col items-stretch gap-1.5">
      <ThreadListNew />
      <ThreadListItems />
    </ThreadListPrimitive.Root>)
  );
};

const ThreadListNew = () => {
  return (
    (<ThreadListPrimitive.New asChild>
      <Button
        className="data-[active]:bg-muted hover:bg-muted flex items-center justify-start gap-1 rounded-lg px-2.5 py-2 text-start"
        variant="ghost">
        <PlusIcon />
        New Thread
      </Button>
    </ThreadListPrimitive.New>)
  );
};

const ThreadListItems = () => {
  return <ThreadListPrimitive.Items components={{ ThreadListItem }} />;
};

const ThreadListItem = () => {
  return (
    (<ThreadListItemPrimitive.Root
      className="data-[active]:bg-muted hover:bg-muted focus-visible:bg-muted focus-visible:ring-ring flex items-center gap-2 rounded-lg transition-all focus-visible:outline-none focus-visible:ring-2">
      <ThreadListItemPrimitive.Trigger className="flex-grow px-3 py-2 text-start">
        <ThreadListItemTitle />
      </ThreadListItemPrimitive.Trigger>
      <ThreadListItemArchive />
    </ThreadListItemPrimitive.Root>)
  );
};

const ThreadListItemTitle = () => {
  return (
    (<p className="text-sm">
      <ThreadListItemPrimitive.Title fallback="New Chat" />
    </p>)
  );
};

const ThreadListItemArchive = () => {
  return (
    (<ThreadListItemPrimitive.Archive asChild>
      <TooltipIconButton
        className="hover:text-primary text-foreground ml-auto mr-3 size-4 p-0"
        variant="ghost"
        tooltip="Archive thread">
        <ArchiveIcon />
      </TooltipIconButton>
    </ThreadListItemPrimitive.Archive>)
  );
};
