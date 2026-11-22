import * as React from "react";
import { AlertTriangle, Trash2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Checkbox } from "../ui/checkbox";

export interface DeleteConfirmationDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  entityName: string;
  consequences: string;
  showPurgeFilesOption?: boolean;
  purgeFilesChecked?: boolean;
  onPurgeFilesToggle?: (checked: boolean) => void;
  purgeFilesLabel?: string;
  onConfirm: () => Promise<void> | void;
  isDeleting?: boolean;
}

export const DeleteConfirmationDialog: React.FC<DeleteConfirmationDialogProps> = ({
  isOpen,
  onOpenChange,
  title,
  entityName,
  consequences,
  showPurgeFilesOption = false,
  purgeFilesChecked = false,
  onPurgeFilesToggle,
  purgeFilesLabel = "Also delete underlying file from SSD storage",
  onConfirm,
  isDeleting = false,
}) => {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md border-destructive/30 bg-card p-6 shadow-2xl">
        <DialogHeader className="space-y-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-destructive/15 text-destructive">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <DialogTitle className="text-base font-semibold text-foreground">
            {title}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground leading-relaxed">
            Are you sure you want to permanently delete{" "}
            <strong className="text-foreground font-mono font-medium">{entityName}</strong>?
          </DialogDescription>
        </DialogHeader>

        <div className="my-3 p-3.5 rounded-lg bg-destructive/5 border border-destructive/20 text-xs text-muted-foreground leading-relaxed space-y-2">
          <p className="font-semibold text-destructive flex items-center gap-1.5">
            <Trash2 className="h-3.5 w-3.5" />
            Deletion Impact:
          </p>
          <p>{consequences}</p>
        </div>

        {showPurgeFilesOption && (
          <div className="py-2">
            <Checkbox
              checked={purgeFilesChecked}
              onCheckedChange={onPurgeFilesToggle}
              label={purgeFilesLabel}
              description="This cannot be undone. External or backup copies are recommended."
            />
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-0 mt-4">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={isDeleting}
            className="text-xs"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={onConfirm}
            loading={isDeleting}
            disabled={isDeleting}
            className="text-xs gap-1.5"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>{isDeleting ? "Deleting..." : "Permanently Delete"}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
