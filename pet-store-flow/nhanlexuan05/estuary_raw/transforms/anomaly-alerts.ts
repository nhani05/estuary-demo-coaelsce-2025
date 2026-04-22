import { IDerivation, Document, SourceFromTxnClean } from 'flow/nhanlexuan05/estuary_raw/anomaly-alerts.ts';

export class Derivation extends IDerivation {
    fromTxnClean(read: { doc: SourceFromTxnClean }): Document[] {
        const doc = read.doc;

        // Chỉ xử lý các giao dịch bất thường
        if (!(doc as any).is_anomaly) return [];

        // Phân loại mức độ nghiêm trọng
        const alertLevel = (doc as any).amount > 500 ? 'HIGH' : 'LOW';

        return [{
            _meta: doc._meta,
            id: doc.id,
            product_id: doc.product_id ?? 'unknown',
            amount: (doc as any).amount,
            alert_level: alertLevel,
            payment_method: (doc as any).payment_method ?? 'unknown',
            transaction_date: (doc as any).transaction_date ?? '',
            created_at: new Date().toISOString(),
        }];
    }
}
