import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { NotFoundPage } from "../components/common/NotFoundPage";

import { DashboardPage } from "../features/dashboard/DashboardPage";
import { VideoLibraryPage } from "../features/videos/VideoLibraryPage";
import { UploadPage } from "../features/videos/UploadPage";
import { VideoDetailPage } from "../features/videos/VideoDetailPage";
import { TranscriptViewerPage } from "../features/transcripts/TranscriptViewerPage";
import { HighlightsPage } from "../features/highlights/HighlightsPage";
import { ClipsLibraryPage } from "../features/clips/ClipsLibraryPage";
import { StudioPage } from "../features/clips/StudioPage";
import { ExportsPage } from "../features/exports/ExportsPage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { StoragePage } from "../features/settings/StoragePage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    errorElement: <NotFoundPage />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: "videos",
        element: <VideoLibraryPage />,
      },
      {
        path: "upload",
        element: <UploadPage />,
      },
      {
        path: "video/:id",
        element: <VideoDetailPage />,
      },
      {
        path: "video/:id/transcript",
        element: <TranscriptViewerPage />,
      },
      {
        path: "video/:id/highlights",
        element: <HighlightsPage />,
      },
      {
        path: "clips",
        element: <ClipsLibraryPage />,
      },
      {
        path: "studio/:clipId",
        element: <StudioPage />,
      },
      {
        path: "exports",
        element: <ExportsPage />,
      },
      {
        path: "settings",
        element: <SettingsPage />,
      },
      {
        path: "settings/storage",
        element: <StoragePage />,
      },
      {
        path: "*",
        element: <NotFoundPage />,
      },
    ],
  },
], {
  future: {
    v7_relativeSplatPath: true,
  },
});
