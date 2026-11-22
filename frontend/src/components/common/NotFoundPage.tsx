import React from "react";
import { Link } from "react-router-dom";
import { Compass, Home, ArrowLeft } from "lucide-react";
import { Button } from "../ui/button";

export const NotFoundPage: React.FC = () => {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-8 text-center animate-in fade-in">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-secondary text-primary border border-border shadow-md">
        <Compass className="h-8 w-8" />
      </div>
      <h1 className="text-3xl font-bold tracking-tight text-foreground font-mono">404</h1>
      <h2 className="mt-2 text-lg font-semibold text-foreground">Route Not Found</h2>
      <p className="mt-2 text-xs text-muted-foreground max-w-md leading-relaxed">
        The requested URL path does not exist in Clipsly. Return to the dashboard or inspect your active navigation routes.
      </p>

      <div className="mt-6 flex items-center gap-3">
        <Button asChild variant="outline" size="sm">
          <Link to=".." relative="path" className="gap-2">
            <ArrowLeft className="h-3.5 w-3.5" />
            Go Back
          </Link>
        </Button>
        <Button asChild size="sm">
          <Link to="/" className="gap-2">
            <Home className="h-3.5 w-3.5" />
            Return to Dashboard
          </Link>
        </Button>
      </div>
    </div>
  );
};
