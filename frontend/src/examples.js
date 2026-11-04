// Примеры входа из examples/input/ — попадают в сборку фронтенда при `vite build`
// (в Docker папка examples/ копируется в образ сборки, см. frontend/Dockerfile).
import tm210 from "../../examples/input/tm-210.json?raw";
import megeon from "../../examples/input/megeon-51020.json?raw";
import incomplete from "../../examples/input/incomplete-pd100.json?raw";

export const EXAMPLES = [
  { label: "Пример: ТМ-210", text: tm210 },
  { label: "Пример: МЕГЕОН 51020", text: megeon },
  { label: "Пример: неполные данные", text: incomplete },
];
