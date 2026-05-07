"""DLinear模型推理模块"""
import torch
import torch.nn as nn


class MovingAvg(nn.Module):
    """移动平均层"""
    def __init__(self, kernel_size, stride=1):
        super().__init__()
        self.kernel_size = kernel_size
        self.avg = nn.AvgPool1d(kernel_size=kernel_size, stride=stride, padding=0)
        self.padding = nn.ReplicationPad1d((kernel_size - 1) // 2)

    def forward(self, x):
        # x: (batch, seq_len, channels)
        x = x.permute(0, 2, 1)  # (batch, channels, seq_len)
        x = self.padding(x)
        x = self.avg(x)
        x = x.permute(0, 2, 1)  # (batch, seq_len, channels)
        return x


class SeriesDecomp(nn.Module):
    """序列分解：趋势 + 季节"""
    def __init__(self, kernel_size):
        super().__init__()
        self.moving_avg = MovingAvg(kernel_size, stride=1)

    def forward(self, x):
        trend = self.moving_avg(x)
        seasonal = x - trend
        return seasonal, trend


class DLinearModel(nn.Module):
    """DLinear模型"""
    def __init__(self, input_size, seq_len=96, pred_len=24, individual=False, kernel_size=25):
        super().__init__()
        self.seq_len = seq_len
        self.pred_len = pred_len
        self.individual = individual

        self.decomposition = SeriesDecomp(kernel_size)

        if individual:
            self.Linear_Seasonal = nn.ModuleList([
                nn.Linear(self.seq_len, self.pred_len) for _ in range(input_size)
            ])
            self.Linear_Trend = nn.ModuleList([
                nn.Linear(self.seq_len, self.pred_len) for _ in range(input_size)
            ])
        else:
            self.Linear_Seasonal = nn.Linear(self.seq_len, self.pred_len)
            self.Linear_Trend = nn.Linear(self.seq_len, self.pred_len)

        # 只输出Active_Power
        self.output_proj = nn.Linear(input_size, 1)

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        seasonal_init, trend_init = self.decomposition(x)

        # (batch, seq_len, features) -> (batch, features, seq_len)
        seasonal_init = seasonal_init.permute(0, 2, 1)
        trend_init = trend_init.permute(0, 2, 1)

        if self.individual:
            seasonal_output = torch.zeros(
                [seasonal_init.size(0), seasonal_init.size(1), self.pred_len],
                dtype=seasonal_init.dtype
            ).to(seasonal_init.device)
            trend_output = torch.zeros(
                [trend_init.size(0), trend_init.size(1), self.pred_len],
                dtype=trend_init.dtype
            ).to(trend_init.device)
            for idx in range(seasonal_init.size(1)):
                seasonal_output[:, idx, :] = self.Linear_Seasonal[idx](seasonal_init[:, idx, :])
                trend_output[:, idx, :] = self.Linear_Trend[idx](trend_init[:, idx, :])
        else:
            seasonal_output = self.Linear_Seasonal(seasonal_init)
            trend_output = self.Linear_Trend(trend_init)

        # (batch, features, pred_len) -> (batch, pred_len, features)
        output = seasonal_output + trend_output
        output = output.permute(0, 2, 1)  # (batch, pred_len, features)

        # 投影到单输出
        output = self.output_proj(output)  # (batch, pred_len, 1)
        return output
