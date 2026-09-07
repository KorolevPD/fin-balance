import { CATEGORIES, DEFAULT_CATEGORY } from './categories';

test('DEFAULT_CATEGORY присутствует в списке CATEGORIES', () => {
  expect(CATEGORIES).toContain(DEFAULT_CATEGORY);
});

test('CATEGORIES не содержит дубликатов', () => {
  expect(new Set(CATEGORIES).size).toBe(CATEGORIES.length);
});