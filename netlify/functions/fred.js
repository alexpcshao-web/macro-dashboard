exports.handler = async (event) => {
  const { series_id, limit = 26 } = event.queryStringParameters || {};
  if (!series_id) return { statusCode: 400, body: 'Missing series_id' };
  const key = process.env.FRED_API_KEY;
  const url = `https://api.stlouisfed.org/fred/series/observations?series_id=${series_id}&api_key=${key}&file_type=json&sort_order=desc&limit=${limit}`;
  try {
    const res = await fetch(url);
    const data = await res.json();
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    };
  } catch (e) {
    return { statusCode: 500, body: e.message };
  }
};
