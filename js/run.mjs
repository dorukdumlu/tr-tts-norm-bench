// Reads a JSON array of lines on stdin, writes the normalized lines as a JSON array.
import { normalize } from "@ozgurguler/trnorm";

let input = "";
process.stdin.setEncoding("utf8");
for await (const chunk of process.stdin) input += chunk;
process.stdout.write(JSON.stringify(JSON.parse(input).map((t) => normalize(t))));
