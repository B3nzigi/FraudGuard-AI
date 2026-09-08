const BASE_URL = 'http://localhost:8080/api/v1';

export const fetchTransactions = async () => {
    const response = await fetch(`${BASE_URL}/transactions`);
    if (!response.ok) throw new Error('Failed to fetch transactions');
    return response.json();
};

export const fetchForecastData = async ({
    timeframe = '7d',
    cutoff = 0.75,
    enforceMpesa = true,
    blockVpn = false,
} = {}) => {
    const params = new URLSearchParams({
        timeframe,
        cutoff: String(cutoff),
        enforce_mpesa: String(enforceMpesa),
        block_vpn: String(blockVpn),
    });

    const response = await fetch(`${BASE_URL}/forecast?${params.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch ML Forecast Data');
    return response.json();
};
