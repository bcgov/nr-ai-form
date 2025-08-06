const express = require('express');
import { Router, Request, Response, NextFunction } from "express";
const router = Router();

import { assist } from '../controllers/webform';


router.post("/webform/:formId/assist/:fieldId",
  express.json(),
  async (req: Request, res: Response, next: NextFunction) => {
    await assist(req, res, next);
  }
);

// router.get("/webform/:id", (req: Request, res: Response) => {
//   console.log(req.query);
//   const response = {
//     id: req.params.id,
//     blah: 'blah blah'
//   }
//   res.status(200).json(response);
// });

export default router;
