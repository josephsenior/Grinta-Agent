import {
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
} from "@heroui/react";
import React from "react";
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
  contentClassName = "max-w-[30rem] p-8 backdrop-blur-xl",
  bodyClassName = "px-0 py-6",
  isDismissable = true,
  subtitle = undefined,
  actions = [],
  children = null,
  testID,
}: BaseModalProps) {
  return (
    <Modal
      data-testid={testID}
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      isDismissable={isDismissable}
      backdrop="blur"
      hideCloseButton
      size="sm"
      className="bg-gradient-to-br from-grey-900/95 to-grey-950/98 backdrop-blur-xl border border-grey-700/30 rounded-2xl shadow-2xl"
      classNames={{
        backdrop: "bg-grey-950/60 backdrop-blur-lg",
        base: "border border-grey-700/20 shadow-xl",
      }}
    >
      <ModalContent className={contentClassName}>
        {(closeModal) => (
          <>
            {title && (
              <ModalHeader className="flex flex-col p-0">
                <HeaderContent maintitle={title} subtitle={subtitle} />
              </ModalHeader>
            )}

            <ModalBody className={bodyClassName}>{children}</ModalBody>

            {actions && actions.length > 0 && (
              <ModalFooter className="flex-row flex justify-start p-0">
                <FooterContent actions={actions} closeModal={closeModal} />
              </ModalFooter>
            )}
          </>
        )}
      </ModalContent>
    </Modal>
  );
}
