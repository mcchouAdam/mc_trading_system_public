/* eslint-disable */
/* tslint:disable */
// @ts-nocheck
/*
 * ---------------------------------------------------------------
 * ## THIS FILE WAS GENERATED VIA SWAGGER-TYPESCRIPT-API        ##
 * ##                                                           ##
 * ## AUTHOR: acacode                                           ##
 * ## SOURCE: https://github.com/acacode/swagger-typescript-api ##
 * ---------------------------------------------------------------
 */

export interface ActiveStrategyMetadata {
  active?: boolean;
  epic?: string | null;
  id?: string | null;
  name?: string | null;
  /** @format double */
  position_size?: number;
  resolution?: string | null;
  sizing_type?: string | null;
  use_ml?: boolean;
}

export interface AvailableStrategy {
  default_parameters?: Record<string, number>;
  /** @format double */
  default_position_size?: number;
  default_sizing_type?: string | null;
  name?: string | null;
  supports_ml?: boolean;
}

export interface OhlcDataSubscription {
  epic?: string | null;
  resolution?: string | null;
}

export interface OpenTrade {
  /** @format double */
  current_price?: number;
  deal_id?: string | null;
  direction?: string | null;
  /** @format double */
  entry_price?: number;
  entry_time?: string | null;
  epic?: string | null;
  /** @format double */
  profit_level?: number | null;
  resolution?: string | null;
  /** @format double */
  size?: number;
  /** @format double */
  stop_level?: number | null;
  strategy?: string | null;
  /** @format double */
  unrealized_pnl?: number;
}

export interface RiskLimitUpdate {
  daily_limit_enabled?: boolean;
  /** @format double */
  daily_limit_pct?: number;
  monthly_limit_enabled?: boolean;
  /** @format double */
  monthly_limit_pct?: number;
}

export interface RiskStatus {
  account_id?: string | null;
  /** @format double */
  balance?: number;
  can_resume?: boolean;
  daily_limit_enabled?: boolean;
  /** @format double */
  daily_limit_pct?: number;
  /** @format double */
  daily_pnl_pct?: number;
  /** @format double */
  equity?: number;
  halt_reason?: string | null;
  is_halted?: boolean;
  is_resume_override?: boolean;
  monthly_limit_enabled?: boolean;
  /** @format double */
  monthly_limit_pct?: number;
  /** @format double */
  monthly_pnl_pct?: number;
  /** @format double */
  start_day_balance?: number;
  /** @format double */
  start_month_balance?: number;
}

export interface StrategyInstance {
  active?: boolean;
  epic?: string | null;
  id?: string | null;
  name?: string | null;
  parameters?: Record<string, number>;
  /** @format double */
  position_size?: number;
  resolution?: string | null;
  sizing_type?: string | null;
  use_ml?: boolean;
}

export interface TradingSettings {
  /** @format double */
  default_size?: number;
  /** @format double */
  fixed_leverage_factor?: number;
  /** @format double */
  risk_pct_per_trade?: number;
  use_dynamic_sizing?: boolean;
}

import type {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  HeadersDefaults,
  ResponseType,
} from "axios";
import axios from "axios";

export type QueryParamsType = Record<string | number, any>;

export interface FullRequestParams
  extends Omit<AxiosRequestConfig, "data" | "params" | "url" | "responseType"> {
  /** set parameter to `true` for call `securityWorker` for this request */
  secure?: boolean;
  /** request path */
  path: string;
  /** content type of request body */
  type?: ContentType;
  /** query params */
  query?: QueryParamsType;
  /** format of response (i.e. response.json() -> format: "json") */
  format?: ResponseType;
  /** request body */
  body?: unknown;
}

export type RequestParams = Omit<
  FullRequestParams,
  "body" | "method" | "query" | "path"
>;

export interface ApiConfig<SecurityDataType = unknown>
  extends Omit<AxiosRequestConfig, "data" | "cancelToken"> {
  securityWorker?: (
    securityData: SecurityDataType | null,
  ) => Promise<AxiosRequestConfig | void> | AxiosRequestConfig | void;
  secure?: boolean;
  format?: ResponseType;
}

export enum ContentType {
  Json = "application/json",
  JsonApi = "application/vnd.api+json",
  FormData = "multipart/form-data",
  UrlEncoded = "application/x-www-form-urlencoded",
  Text = "text/plain",
}

export class HttpClient<SecurityDataType = unknown> {
  public instance: AxiosInstance;
  private securityData: SecurityDataType | null = null;
  private securityWorker?: ApiConfig<SecurityDataType>["securityWorker"];
  private secure?: boolean;
  private format?: ResponseType;

  constructor({
    securityWorker,
    secure,
    format,
    ...axiosConfig
  }: ApiConfig<SecurityDataType> = {}) {
    this.instance = axios.create({
      ...axiosConfig,
      baseURL: axiosConfig.baseURL || "",
    });
    this.secure = secure;
    this.format = format;
    this.securityWorker = securityWorker;
  }

  public setSecurityData = (data: SecurityDataType | null) => {
    this.securityData = data;
  };

  protected mergeRequestParams(
    params1: AxiosRequestConfig,
    params2?: AxiosRequestConfig,
  ): AxiosRequestConfig {
    const method = params1.method || (params2 && params2.method);

    return {
      ...this.instance.defaults,
      ...params1,
      ...(params2 || {}),
      headers: {
        ...((method &&
          this.instance.defaults.headers[
          method.toLowerCase() as keyof HeadersDefaults
          ]) ||
          {}),
        ...(params1.headers || {}),
        ...((params2 && params2.headers) || {}),
      },
    };
  }

  protected stringifyFormItem(formItem: unknown) {
    if (typeof formItem === "object" && formItem !== null) {
      return JSON.stringify(formItem);
    } else {
      return `${formItem}`;
    }
  }

  protected createFormData(input: Record<string, unknown>): FormData {
    if (input instanceof FormData) {
      return input;
    }
    return Object.keys(input || {}).reduce((formData, key) => {
      const property = input[key];
      const propertyContent: any[] =
        property instanceof Array ? property : [property];

      for (const formItem of propertyContent) {
        const isFileType = formItem instanceof Blob || formItem instanceof File;
        formData.append(
          key,
          isFileType ? formItem : this.stringifyFormItem(formItem),
        );
      }

      return formData;
    }, new FormData());
  }

  public request = async <T = any, _E = any>({
    secure,
    path,
    type,
    query,
    format,
    body,
    ...params
  }: FullRequestParams): Promise<AxiosResponse<T>> => {
    const secureParams =
      ((typeof secure === "boolean" ? secure : this.secure) &&
        this.securityWorker &&
        (await this.securityWorker(this.securityData))) ||
      {};
    const requestParams = this.mergeRequestParams(params, secureParams);
    const responseFormat = format || this.format || undefined;

    if (
      type === ContentType.FormData &&
      body &&
      body !== null &&
      typeof body === "object"
    ) {
      body = this.createFormData(body as Record<string, unknown>);
    }

    if (
      type === ContentType.Text &&
      body &&
      body !== null &&
      typeof body !== "string"
    ) {
      body = JSON.stringify(body);
    }

    return this.instance.request({
      ...requestParams,
      headers: {
        ...(requestParams.headers || {}),
        ...(type ? { "Content-Type": type } : {}),
      },
      params: query,
      responseType: responseFormat,
      data: body,
      url: path,
    });
  };
}

/**
 * @title ApiServer
 * @version 1.0
 */
export class Api<
  SecurityDataType extends unknown,
> extends HttpClient<SecurityDataType> {
  api = {
    /**
     * No description
     *
     * @tags Market
     * @name MarketKlinesList
     * @request GET:/api/market/klines
     */
    marketKlinesList: (
      query?: {
        /** @default "US100" */
        epic?: string;
        /**
         * @format int32
         * @default 200
         */
        max_bars?: number;
        /** @default "MINUTE" */
        resolution?: string;
        /** @format int64 */
        to?: number;
      },
      params: RequestParams = {},
    ) =>
      this.request<void, any>({
        path: `/api/market/klines`,
        method: "GET",
        query: query,
        ...params,
      }),

    /**
     * No description
     *
     * @tags Market
     * @name MarketSearchList
     * @request GET:/api/market/search
     */
    marketSearchList: (
      query?: {
        q?: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<void, any>({
        path: `/api/market/search`,
        method: "GET",
        query: query,
        ...params,
      }),

    /**
     * No description
     *
     * @tags Risk
     * @name RiskStatusList
     * @request GET:/api/risk/status
     */
    riskStatusList: (params: RequestParams = {}) =>
      this.request<RiskStatus, any>({
        path: `/api/risk/status`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags Risk
     * @name RiskResumeCreate
     * @request POST:/api/risk/resume
     */
    riskResumeCreate: (params: RequestParams = {}) =>
      this.request<void, any>({
        path: `/api/risk/resume`,
        method: "POST",
        ...params,
      }),

    /**
     * No description
     *
     * @tags Risk
     * @name RiskLimitsCreate
     * @request POST:/api/risk/limits
     */
    riskLimitsCreate: (data: RiskLimitUpdate, params: RequestParams = {}) =>
      this.request<void, any>({
        path: `/api/risk/limits`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        ...params,
      }),

    /**
     * No description
     *
     * @tags Risk
     * @name RiskHaltCreate
     * @request POST:/api/risk/halt
     */
    riskHaltCreate: (params: RequestParams = {}) =>
      this.request<void, any>({
        path: `/api/risk/halt`,
        method: "POST",
        ...params,
      }),

    /**
     * No description
     *
     * @tags System
     * @name SystemWatchlistList
     * @request GET:/api/system/watchlist
     */
    systemWatchlistList: (params: RequestParams = {}) =>
      this.request<string[], any>({
        path: `/api/system/watchlist`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags System
     * @name SystemStrategiesList
     * @request GET:/api/system/strategies
     */
    systemStrategiesList: (params: RequestParams = {}) =>
      this.request<StrategyInstance[], any>({
        path: `/api/system/strategies`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags System
     * @name SystemStrategiesCreate
     * @request POST:/api/system/strategies
     */
    systemStrategiesCreate: (
      data: StrategyInstance[],
      params: RequestParams = {},
    ) =>
      this.request<void, any>({
        path: `/api/system/strategies`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        ...params,
      }),

    /**
     * No description
     *
     * @tags System
     * @name SystemSubscriptionMarketDataList
     * @request GET:/api/system/subscription/market-data
     */
    systemSubscriptionMarketDataList: (params: RequestParams = {}) =>
      this.request<string[], any>({
        path: `/api/system/subscription/market-data`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags System
     * @name SystemSubscriptionMarketDataCreate
     * @request POST:/api/system/subscription/market-data
     */
    systemSubscriptionMarketDataCreate: (
      data: string[],
      params: RequestParams = {},
    ) =>
      this.request<void, any>({
        path: `/api/system/subscription/market-data`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        ...params,
      }),

    /**
     * No description
     *
     * @tags System
     * @name SystemSubscriptionOhlcDataList
     * @request GET:/api/system/subscription/ohlc-data
     */
    systemSubscriptionOhlcDataList: (params: RequestParams = {}) =>
      this.request<OhlcDataSubscription[], any>({
        path: `/api/system/subscription/ohlc-data`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags System
     * @name SystemSubscriptionOhlcDataCreate
     * @request POST:/api/system/subscription/ohlc-data
     */
    systemSubscriptionOhlcDataCreate: (
      data: OhlcDataSubscription[],
      params: RequestParams = {},
    ) =>
      this.request<void, any>({
        path: `/api/system/subscription/ohlc-data`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        ...params,
      }),

    /**
     * No description
     *
     * @tags System
     * @name SystemAvailableStrategiesList
     * @request GET:/api/system/available-strategies
     */
    systemAvailableStrategiesList: (params: RequestParams = {}) =>
      this.request<AvailableStrategy[], any>({
        path: `/api/system/available-strategies`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags System
     * @name SystemSupportedEpicsList
     * @request GET:/api/system/supported-epics
     */
    systemSupportedEpicsList: (params: RequestParams = {}) =>
      this.request<string[], any>({
        path: `/api/system/supported-epics`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags System
     * @name SystemActiveStrategiesList
     * @request GET:/api/system/active_strategies
     */
    systemActiveStrategiesList: (params: RequestParams = {}) =>
      this.request<ActiveStrategyMetadata[], any>({
        path: `/api/system/active_strategies`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags System
     * @name SystemTradingSettingsList
     * @request GET:/api/system/trading-settings
     */
    systemTradingSettingsList: (params: RequestParams = {}) =>
      this.request<TradingSettings, any>({
        path: `/api/system/trading-settings`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags System
     * @name SystemTradingSettingsCreate
     * @request POST:/api/system/trading-settings
     */
    systemTradingSettingsCreate: (
      data: TradingSettings,
      params: RequestParams = {},
    ) =>
      this.request<void, any>({
        path: `/api/system/trading-settings`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        ...params,
      }),

    /**
     * No description
     *
     * @tags Trade
     * @name TradePingList
     * @request GET:/api/trade/ping
     */
    tradePingList: (params: RequestParams = {}) =>
      this.request<void, any>({
        path: `/api/trade/ping`,
        method: "GET",
        ...params,
      }),

    /**
     * No description
     *
     * @tags Trade
     * @name TradeOpenList
     * @request GET:/api/trade/open
     */
    tradeOpenList: (params: RequestParams = {}) =>
      this.request<OpenTrade[], any>({
        path: `/api/trade/open`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags Trade
     * @name TradeClosedList
     * @request GET:/api/trade/closed
     */
    tradeClosedList: (
      query?: {
        from_date?: string;
        /**
         * @format int32
         * @default 1
         */
        page?: number;
        /**
         * @format int32
         * @default 10
         */
        pageSize?: number;
        to_date?: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<void, any>({
        path: `/api/trade/closed`,
        method: "GET",
        query: query,
        ...params,
      }),

    /**
     * No description
     *
     * @tags Trade
     * @name TradeCloseDelete
     * @request DELETE:/api/trade/close/{deal_id}
     */
    tradeCloseDelete: (
      dealId: string,
      query?: {
        epic?: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<void, any>({
        path: `/api/trade/close/${dealId}`,
        method: "DELETE",
        query: query,
        ...params,
      }),

    /**
     * No description
     *
     * @tags Trade
     * @name TradeOrderCreate
     * @request POST:/api/trade/order
     */
    tradeOrderCreate: (data: any, params: RequestParams = {}) =>
      this.request<void, any>({
        path: `/api/trade/order`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        ...params,
      }),

    /**
     * No description
     *
     * @tags Trade
     * @name TradePositionLimitsUpdate
     * @request PUT:/api/trade/position/{dealId}/limits
     */
    tradePositionLimitsUpdate: (
      dealId: string,
      data: any,
      params: RequestParams = {},
    ) =>
      this.request<void, any>({
        path: `/api/trade/position/${dealId}/limits`,
        method: "PUT",
        body: data,
        type: ContentType.Json,
        ...params,
      }),
  };
}
