export default function Container({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main
      style={{
        maxWidth: 900,
        margin: "40px auto",
        padding: 20,
      }}
    >
      {children}
    </main>
  );
}