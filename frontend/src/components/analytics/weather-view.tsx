"use client";

import { useMemo } from "react";
import type { ChartTokens } from "@/components/charts/tokens";
import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { orDash } from "@/components/ui/value";
import { fetchWeather, type AnalyticsRef, type Weather } from "./data";
import { AnalyticsChart, ChartFrame, RequestState } from "./chart-frame";
import { useAnalytics } from "./hooks";
import { buildWeatherOption } from "./options";

export function WeatherView({ refs }: { refs: AnalyticsRef }) {
  const query = useAnalytics("weather", refs, () => fetchWeather(refs));
  return (
    <RequestState query={query} isEmpty={(d) => d.samples.length === 0} emptyTitle="No weather data">
      {(data) => <WeatherPanel data={data} />}
    </RequestState>
  );
}

const time = (ts: string) => new Date(ts).toISOString().slice(11, 16);

function WeatherPanel({ data }: { data: Weather }) {
  const option = useMemo(() => (t: ChartTokens) => buildWeatherOption(data, t), [data]);
  const title = `${data.session.year} ${data.session.round_name}: air and track temperature`;
  const rain = data.samples.some((s) => s.rainfall);
  return (
    <ChartFrame
      title={title}
      chart={<AnalyticsChart option={option} label={`${title}. A table is available.`} />}
      table={
        <DataTable caption="Weather samples" minWidth="34rem">
          <thead>
            <tr>
              <Th>Time (UTC)</Th>
              <Th align="right">Air °C</Th>
              <Th align="right">Track °C</Th>
              <Th align="right">Humidity %</Th>
              <Th align="right">Wind m/s</Th>
              <Th>Rain</Th>
            </tr>
          </thead>
          <tbody>
            {data.samples.map((s) => (
              <Tr key={s.ts}>
                <RowTh className="timing">{time(s.ts)}</RowTh>
                <Td align="right" className="timing">{orDash(s.air_temperature)}</Td>
                <Td align="right" className="timing">{orDash(s.track_temperature)}</Td>
                <Td align="right" className="timing">{orDash(s.humidity)}</Td>
                <Td align="right" className="timing">{orDash(s.wind_speed)}</Td>
                <Td>{s.rainfall ? "Rain" : "Dry"}</Td>
              </Tr>
            ))}
          </tbody>
        </DataTable>
      }
      legend={<p className="text-sm text-muted">{rain ? "Rain was recorded during this session." : "No rain recorded."}</p>}
    />
  );
}
