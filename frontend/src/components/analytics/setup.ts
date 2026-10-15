import * as echarts from "echarts/core";
import { ScatterChart } from "echarts/charts";
import { DataZoomComponent, MarkAreaComponent } from "echarts/components";

/** Chart types and components the analytics views need on top of the shared setup. */
echarts.use([ScatterChart, DataZoomComponent, MarkAreaComponent]);
