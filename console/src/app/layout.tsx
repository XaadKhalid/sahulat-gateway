import './globals.css';
import { RootProviders } from '@/components/providers';

export const metadata = {
  title: 'Sahulat Gateway',
  description: 'Control plane for the Sahulat conversational agent gateway.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="antialiased">
      <body>
        <RootProviders>{children}</RootProviders>
      </body>
    </html>
  );
}
