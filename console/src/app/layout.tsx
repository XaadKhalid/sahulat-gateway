import './globals.css';
import { RootProviders } from '@/components/providers';

export const metadata = {
  title: 'Sahulat Gateway Admin',
  description: 'Control plane for the Sahulat conversational gateway',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <RootProviders>{children}</RootProviders>
      </body>
    </html>
  );
}
