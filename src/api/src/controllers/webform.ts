import { Request, Response, NextFunction } from 'express';

import { aiPrompt } from '../services/aiService';

/**
 * * Assists with a webform field using AI
 * @param {Request} req - The request object
 * @param {Response} res - The response object
 * @param {Function} next - The next middleware function
 * @returns {Promise<void>}
 */
export const assist = async (req: Request, res: Response, next: NextFunction) => {
  try {

    // entire webform data
    const data = req.body;

    // build a prompt somehow using a definition for the form
    let prompt, aiResponse;
    if (data.fieldId === '0') {
      if (data.formData['0'].toLowerCase() !== 'victoria' && data.formData['0'].toLowerCase() !== 'vancouver') {
        prompt = `List some cities in British Columbia`;
        aiResponse = (await aiPrompt(prompt)).choices[0].message.content;
      }
      else {
        aiResponse = 'This response looks valid';
      };
    }
    if (data.fieldId === '1') {
      prompt = `Show me ${req.body.fieldHelp} in ${data.formData['0']}`
      aiResponse = (await aiPrompt(prompt)).choices[0].message.content;
    }

    // create API response
    const response = {
      formId: req.params.formId,
      fieldId: req.params.fieldId,
      aiResponse: aiResponse,
    }
    res.status(201).json(response);

  } catch (error) {
    console.error('Error in assist:', error);
    next(error);
  }
};
