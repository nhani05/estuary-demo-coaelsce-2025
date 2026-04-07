import { IDerivation, Document, SourceFromTransactions } from 'flow/nhanlexuan05/estuary_raw/txn-clean.ts';

export class Derivation extends IDerivation {
    fromTransactions(read: { doc: SourceFromTransactions }): Document[] {
        const doc = read.doc;

        if (!doc.amount || doc.amount <= 0) return [];

        return [{
            _meta: doc._meta,
            id: (doc as any)._id?.$oid ?? String((doc as any)._id),
            product_id: (doc as any).product_id ?? 'unknown',
            amount: doc.amount,
            is_anomaly: doc.amount > 500 || doc.amount < 5,
            transaction_date: (doc as any).transaction_date
                ? new Date((doc as any).transaction_date).toISOString()
                : new Date().toISOString(),
            payment_method: (doc as any).payment_method ?? 'unknown',
            transformed_at: new Date().toISOString(),
        }];
    }
}
