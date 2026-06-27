import "./globals.css";

export const metadata = {
  title: "HFU Anatomy Chatbot",
  description: "Locally grounded anatomy assistant",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
