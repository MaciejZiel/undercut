import * as echarts from "echarts/core";
import { LineChart, BarChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent, AxisPointerComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([LineChart, BarChart, GridComponent, LegendComponent, TooltipComponent, AxisPointerComponent, CanvasRenderer]);

export { echarts };
