import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
} from "#/components/ui/dialog";
import React from "react";
import { cn } from "#/utils/utils";
import { Action, FooterContent } from "./footer-content";
import { HeaderContent } from "./header-content";

interface BaseModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  title: string;
  contentClassName?: string;
  bodyClassName?: string;
  isDismissable?: boolean;
  subtitle?: string;
  actions?: Action[];
  children?: React.ReactNode;
  testID?: string;
}

export function BaseModal({
  isOpen,
  onOpenChange,
  title,
  contentClassName = "max-w-[30rem]",
  bodyClassName = "px-0 py-6",
  isDismissable = true,
  subtitle = undefined,
  actions = [],
  children = null,
  testID,
}: BaseModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent data-testid={testID} className={cn("p-6 sm:p-8", contentClassName)}>
        {title && (
          <DialogHeader className="flex flex-col p-0">
            <HeaderContent maintitle={title} subtitle={subtitle} />
          </DialogHeader>
        )}

        <div className={bodyClassName}>{children}</div>

        {actions && actions.length > 0 && (
          <DialogFooter className="flex-row flex justify-start p-0">
            <FooterContent actions={actions} closeModal={() => onOpenChange(false)} />
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
