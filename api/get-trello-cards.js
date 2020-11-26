import fetch from "node-fetch";

export default (req, res) => {
  fetch(
    `https://api.trello.com/1/lists/5fbf83d7da8d9d778ba95628/cards?key=${process.env.TRELLO_KEY}&token=${process.env.TRELLO_TOKEN}`
  )
    .then((response) => response.json())
    .then((result) => {
      const list = result.map((each) => {
        return `<li>${each.name}</li>`;
      });
      const height = (24 + 4) * list.length;
      res.setHeader("Content-Type", "image/svg+xml");
      res.status(200).send(
        `
        <svg fill="none" viewBox="0 0 350 ${height}" width="350" height="${height}" xmlns="http://www.w3.org/2000/svg">
          <foreignObject height="100%" width="100%">
            <div xmlns="http://www.w3.org/1999/xhtml">
              <style>
              ul {
                box-sizing: border-box;
                color: rgb(36, 41, 46);
                font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif, Apple Color Emoji, Segoe UI Emoji;
                font-size: 16px;
                line-height: 24px;
                margin-bottom: 16px;
                margin-top: 0px;
                overflow-wrap: break-word;
                padding-left: 32px;
              }
              li {
                box-sizing: border-box;
                color: rgb(36, 41, 46);
                font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif, Apple Color Emoji, Segoe UI Emoji;
                font-size: 16px;
                line-height: 24px;
                overflow-wrap: break-word;
              }
              </style>
              <ul>
                ${list.reduce((acc, each) => acc + each, "")}
              </ul>
            </div>
          </foreignObject>
        </svg>
        `
      );
    })
    .catch((err) => {
      console.error(err);
      res.status(500).send("Something went wrong...");
    });
};
