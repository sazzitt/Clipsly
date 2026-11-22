import * as React from "react";
import { Badge } from "../ui/badge";

export interface EntityStatusBadgeProps {
  status: string;
  className?: string;
}

export const EntityStatusBadge: React.FC<EntityStatusBadgeProps> = ({ status, className }) => {
  const s = (status || "").toUpperCase();

  switch (s) {
    case "READY":
    case "COMPLETED":
    case "EXPORTED":
      return <Badge variant="success" className={className}>Ready</Badge>;

    case "PROCESSING":
    case "RENDERING":
    case "EXTRACTING_AUDIO":
    case "TRANSCRIBING":
    case "SCORING":
      return <Badge variant="warning" className={className}>Processing</Badge>;

    case "FAILED":
    case "ERROR":
      return <Badge variant="destructive" className={className}>Failed</Badge>;

    case "CANCELLED":
      return <Badge variant="warning" className={className}>Cancelled</Badge>;

    case "QUEUED":
    case "PENDING":
      return <Badge variant="secondary" className={className}>Queued</Badge>;

    case "DRAFT":
      return <Badge variant="outline" className={className}>Draft</Badge>;

    case "UPLOADED":
    default:
      return <Badge variant="secondary" className={className}>{status || "Uploaded"}</Badge>;
  }
};
