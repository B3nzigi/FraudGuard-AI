import { forecastService } from './api';

export const fetchForecastData = async (options = {}) => forecastService.getForecast(options);
