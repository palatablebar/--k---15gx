import { createBrowserRouter, Navigate } from 'react-router-dom';
import { ArchiveShell } from '../components/layout/ArchiveShell';
import { LoginPage } from '../pages/Login';
import { DatasetProfilePage } from '../pages/DatasetProfile';
import { PiiEvidencePage } from '../pages/PiiEvidence';
import { PolicyPreviewPage } from '../pages/PolicyPreview';
import { KAnonymityPage } from '../pages/KAnonymity';
import { ExportsPage } from '../pages/Exports';
import { requireAuth } from './guards';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: <ArchiveShell />,
    loader: requireAuth,
    children: [
      { index: true, element: <Navigate to="/datasets" replace /> },
      { path: 'datasets', element: <DatasetProfilePage /> },
      { path: 'datasets/:tableId/columns/:columnId', element: <PiiEvidencePage /> },
      { path: 'pii-evidence', element: <PiiEvidencePage /> },
      { path: 'policies', element: <PolicyPreviewPage /> },
      { path: 'k-anonymity', element: <KAnonymityPage /> },
      { path: 'exports', element: <ExportsPage /> },
    ],
  },
  { path: '*', element: <Navigate to="/datasets" replace /> },
]);
