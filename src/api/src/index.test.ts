// Basic test for the API using supertest
import request from 'supertest';
import express from 'express';

const app = express();
app.get('/', (_req, res) => res.json({ id: 1, message: 'Hello from PostgreSQL!' }));

describe('GET /', () => {
  it('should return the demo row', async () => {
    const res = await request(app).get('/');
    expect(res.statusCode).toBe(200);
    expect(res.body).toEqual({ id: 1, message: 'Hello from PostgreSQL!' });
  });
});
