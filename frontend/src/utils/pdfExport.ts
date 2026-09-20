import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

export interface ExportPdfOptions {
  element: HTMLElement;
  filename?: string;
}

/**
 * Renders discrete .pdf-page elements into a crisp, unclipped multi-page A4 PDF document.
 */
export async function exportElementToPdf({ element, filename = 'Truck-Trip-Plan-FMCSA-Logs.pdf' }: ExportPdfOptions): Promise<void> {
  if (!element) {
    throw new Error('Target element for PDF export was not found.');
  }

  // Find all discrete pages
  const pageElements = element.querySelectorAll<HTMLElement>('.pdf-page');

  if (!pageElements || pageElements.length === 0) {
    // Fallback: render single container
    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      logging: false,
      backgroundColor: '#FFFFFF',
    });

    const pdf = new jsPDF('p', 'mm', 'a4');
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
    const imgData = canvas.toDataURL('image/jpeg', 0.98);
    pdf.addImage(imgData, 'JPEG', 0, 0, pdfWidth, pdfHeight);
    pdf.save(filename);
    return;
  }

  const pdf = new jsPDF('p', 'mm', 'a4');
  const pdfWidth = pdf.internal.pageSize.getWidth();
  const pdfHeight = pdf.internal.pageSize.getHeight();

  for (let i = 0; i < pageElements.length; i++) {
    const pageEl = pageElements[i];

    const canvas = await html2canvas(pageEl, {
      scale: 2.2, // Crisp high-DPI rendering
      useCORS: true,
      logging: false,
      backgroundColor: '#FFFFFF',
      windowWidth: 820,
    });

    const imgData = canvas.toDataURL('image/jpeg', 0.98);

    if (i > 0) {
      pdf.addPage();
    }

    // Place the page image neatly to fill the A4 page
    pdf.addImage(imgData, 'JPEG', 0, 0, pdfWidth, pdfHeight);
  }

  pdf.save(filename);
}
