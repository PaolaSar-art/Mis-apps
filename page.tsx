"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { DashboardData } from "@/types/dashboard";

import Header from "@/components/layout/Header";
import Container from "@/components/layout/Container";
import Card from "@/components/Card";

export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    apiGet("/api/v1/jugador/dashboard")
      .then(setData)
      .catch(console.error);
  }, []);

  return (
    <>
      <Header />

      <Container>
        {!data && <p>Cargando dashboard...</p>}

        {data && (
          <>
            <Card title="Jugador">
              <p>{data.jugador}</p>
            </Card>

            <Card title="Estado">
              <p>{data.estado}</p>
              <p>Racha: {data.racha_actual}</p>
            </Card>

            <Card title="Wallet">
              <p>${data.saldo_wallet}</p>
            </Card>
          </>
        )}
      </Container>
    </>
  );
}