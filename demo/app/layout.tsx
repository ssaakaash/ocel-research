import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] });
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});
export const metadata: Metadata = {
  title: 'Capstone Risk Twin · Team 1 Review 2',
  description:
    'Interactive synthetic study of cross-object risk observability and intervention hypotheses in educational capstone workflows.',
  openGraph: {
    title: 'Capstone Risk Twin · Team 1',
    description:
      'Explore what cross-object evidence reveals, what flat logs lose, and how synthetic intervention policies compare.',
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
