import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] });
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});
export const metadata: Metadata = {
  title: 'OCEL Capstone Lab · Team 1 Review 2',
  description:
    'Interactive synthetic proof-of-mechanism for object-centric process mining of academic capstones.',
  openGraph: {
    title: 'OCEL Capstone Lab · Team 1',
    description:
      'See what flat event logs lose—and what an object-centric model preserves.',
    images: ['/social-preview.png'],
  },
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        {children}
      </body>
    </html>
  );
}
