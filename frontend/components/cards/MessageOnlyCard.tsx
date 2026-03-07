import styles from './Card.module.css';

interface Props {
    payload: Record<string, unknown>;
    onAccept?: () => void;
    onReject?: () => void;
}

export default function MessageOnlyCard({ payload }: Props) {
    // Return null so the text only renders once in the main chat bubble
    return null;
}
